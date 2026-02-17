# ============================================
# Archivo: modulos/ui_tkinter.py
# Propósito:
#   - UI Tkinter del sistema
#   - Pestañas:
#       1) Clientes (CRUD + Buscar + Import/Export + filtro tipo)
#       2) Mensajería (enviar masivo por tipo_cliente o selección manual)
#       3) Historial (campañas + detalle de envíos)
#       4) Configuración (Gmail + app password + prueba)
# ============================================

from __future__ import annotations

import json
import threading
from queue import Queue

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from .repo_clientes import (
    crear_cliente,
    actualizar_cliente,
    eliminar_cliente,
    listar_clientes,
    buscar_clientes_por_nombre,
    obtener_cliente_por_id,
)

from .importaciones_excel import importar_clientes_excel
from .exportaciones import exportar_clientes_excel, exportar_clientes_pdf
from .repo_logs import registrar_evento

from .correo_gmail import (
    cargar_config_correo,
    guardar_config_correo,
    config_es_valida,
    enviar_correo,
    probar_envio,
)

from .repo_plantillas import (
    listar_plantillas,
    crear_plantilla,
    actualizar_plantilla,
    eliminar_plantilla,
    obtener_plantilla_por_id,
)

from .repo_campanas import (
    crear_campana,
    listar_campanas,
    actualizar_resumen_campana,
)

from .repo_envios import (
    crear_detalle_envios,
    listar_envios_por_campana,
    listar_envios_pendientes,
    marcar_envio_enviado,
    marcar_envio_error,
    contar_estados,
)


def renderizar(texto: str, cliente: dict) -> str:
    """
    Reemplaza variables simples dentro de un texto.
    Variables soportadas:
      {nombre}, {apellidos}, {razon_social}, {rut}, {tipo_cliente}, {email}
    """
    # Preparamos valores con fallback a ""
    mapa = {
        "nombre": str(cliente.get("nombres") or ""),
        "apellidos": str(cliente.get("apellidos") or ""),
        "razon_social": str(cliente.get("razon_social") or ""),
        "rut": str(cliente.get("rut") or ""),
        "tipo_cliente": str(cliente.get("tipo_cliente") or ""),
        "email": str(cliente.get("email") or ""),
    }

    # Reemplazo simple por .replace
    for k, v in mapa.items():
        texto = texto.replace("{" + k + "}", v)

    return texto


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("SGC - Sistema de Gestión de Clientes")
        self.geometry("1200x700")
        self.minsize(1100, 620)

        # Listado visible actual (para exportar)
        self.registros_actuales = []

        # Cliente seleccionado para edición
        self.cliente_id_seleccionado = None

        # Estado de envío en background
        self.cola_envio = Queue()
        self.hilo_envio = None
        self.envio_en_proceso = False

        # Config correo (cargada al inicio)
        self.config_correo = cargar_config_correo()

        self._crear_widgets()

        # Inicializaciones de datos
        self._refrescar_listado_clientes()
        self._refrescar_listado_plantillas()
        self._refrescar_listado_campanas()
        self._refrescar_lista_clientes_para_envio()

        self._cargar_config_en_form()

    # =========================================================
    # Construcción general UI
    # =========================================================

    def _crear_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        # Pestañas
        self.tab_clientes = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_clientes, text="Clientes")

        self.tab_mensajeria = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_mensajeria, text="Mensajería")

        self.tab_historial = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_historial, text="Historial")

        self.tab_config = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_config, text="Configuración")

        # Construir cada pestaña
        self._crear_tab_clientes()
        self._crear_tab_mensajeria()
        self._crear_tab_historial()
        self._crear_tab_config()

    # =========================================================
    # PESTAÑA CLIENTES (igual que antes)
    # =========================================================

    def _crear_tab_clientes(self):
        barra = ttk.Frame(self.tab_clientes)
        barra.pack(fill="x", padx=10, pady=8)

        ttk.Label(barra, text="Buscar (nombre / RUT / email):").pack(side="left")

        self.var_buscar = tk.StringVar()
        ent_buscar = ttk.Entry(barra, textvariable=self.var_buscar, width=35)
        ent_buscar.pack(side="left", padx=8)
        ent_buscar.bind("<Return>", lambda e: self.on_buscar())

        ttk.Button(barra, text="Buscar", command=self.on_buscar).pack(side="left", padx=4)
        ttk.Button(barra, text="Ver todo", command=self.on_ver_todo).pack(side="left", padx=4)

        ttk.Separator(barra, orient="vertical").pack(side="left", fill="y", padx=10)

        ttk.Label(barra, text="Tipo:").pack(side="left")
        self.var_filtro_tipo = tk.StringVar(value="Todos")
        cmb_filtro = ttk.Combobox(
            barra,
            textvariable=self.var_filtro_tipo,
            values=["Todos", "Regular", "Premium", "Corporativo"],
            state="readonly",
            width=14,
        )
        cmb_filtro.pack(side="left", padx=6)
        cmb_filtro.bind("<<ComboboxSelected>>", lambda e: self._refrescar_listado_clientes())

        ttk.Separator(barra, orient="vertical").pack(side="left", fill="y", padx=10)

        ttk.Button(barra, text="Importar Excel", command=self.on_importar_excel).pack(side="left", padx=4)
        ttk.Button(barra, text="Exportar Excel", command=self.on_exportar_excel).pack(side="left", padx=4)
        ttk.Button(barra, text="Exportar PDF", command=self.on_exportar_pdf).pack(side="left", padx=4)

        cont = ttk.Frame(self.tab_clientes)
        cont.pack(fill="both", expand=True, padx=10, pady=8)

        cont.columnconfigure(0, weight=1)
        cont.columnconfigure(1, weight=2)
        cont.rowconfigure(0, weight=1)

        frm = ttk.LabelFrame(cont, text="Formulario Cliente")
        frm.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.var_tipo = tk.StringVar(value="Regular")
        self.var_rut = tk.StringVar()
        self.var_nombres = tk.StringVar()
        self.var_apellidos = tk.StringVar()
        self.var_razon = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_telefono = tk.StringVar()
        self.var_estado = tk.IntVar(value=1)
        self.var_recibe = tk.IntVar(value=1)
        self.var_obs = tk.StringVar()

        r = 0
        ttk.Label(frm, text="Tipo Cliente:").grid(row=r, column=0, sticky="w", padx=8, pady=6)
        cmb_tipo = ttk.Combobox(frm, textvariable=self.var_tipo, values=["Regular", "Premium", "Corporativo"], state="readonly")
        cmb_tipo.grid(row=r, column=1, sticky="ew", padx=8, pady=6)
        cmb_tipo.bind("<<ComboboxSelected>>", lambda e: self._ajustar_form_por_tipo())

        r += 1
        ttk.Label(frm, text="RUT:").grid(row=r, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(frm, textvariable=self.var_rut).grid(row=r, column=1, sticky="ew", padx=8, pady=6)

        r += 1
        ttk.Label(frm, text="Nombres:").grid(row=r, column=0, sticky="w", padx=8, pady=6)
        self.ent_nombres = ttk.Entry(frm, textvariable=self.var_nombres)
        self.ent_nombres.grid(row=r, column=1, sticky="ew", padx=8, pady=6)

        r += 1
        ttk.Label(frm, text="Apellidos:").grid(row=r, column=0, sticky="w", padx=8, pady=6)
        self.ent_apellidos = ttk.Entry(frm, textvariable=self.var_apellidos)
        self.ent_apellidos.grid(row=r, column=1, sticky="ew", padx=8, pady=6)

        r += 1
        ttk.Label(frm, text="Razón Social:").grid(row=r, column=0, sticky="w", padx=8, pady=6)
        self.ent_razon = ttk.Entry(frm, textvariable=self.var_razon)
        self.ent_razon.grid(row=r, column=1, sticky="ew", padx=8, pady=6)

        r += 1
        ttk.Label(frm, text="Email:").grid(row=r, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(frm, textvariable=self.var_email).grid(row=r, column=1, sticky="ew", padx=8, pady=6)

        r += 1
        ttk.Label(frm, text="Teléfono:").grid(row=r, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(frm, textvariable=self.var_telefono).grid(row=r, column=1, sticky="ew", padx=8, pady=6)

        r += 1
        ttk.Checkbutton(frm, text="Activo", variable=self.var_estado).grid(row=r, column=0, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(frm, text="Recibe correos", variable=self.var_recibe).grid(row=r, column=1, sticky="w", padx=8, pady=6)

        r += 1
        ttk.Label(frm, text="Observaciones:").grid(row=r, column=0, sticky="nw", padx=8, pady=6)
        ttk.Entry(frm, textvariable=self.var_obs).grid(row=r, column=1, sticky="ew", padx=8, pady=6)

        r += 1
        btns = ttk.Frame(frm)
        btns.grid(row=r, column=0, columnspan=2, sticky="ew", padx=8, pady=10)

        ttk.Button(btns, text="Agregar", command=self.on_agregar).pack(side="left", padx=4)
        ttk.Button(btns, text="Actualizar", command=self.on_actualizar).pack(side="left", padx=4)
        ttk.Button(btns, text="Eliminar", command=self.on_eliminar).pack(side="left", padx=4)
        ttk.Button(btns, text="Limpiar", command=self.on_limpiar).pack(side="left", padx=4)

        frm.columnconfigure(1, weight=1)
        self._ajustar_form_por_tipo()

        tabla_frame = ttk.LabelFrame(cont, text="Listado de Clientes")
        tabla_frame.grid(row=0, column=1, sticky="nsew")

        columnas = ("cliente_id", "tipo_cliente", "rut", "nombre_mostrado", "email", "telefono", "estado", "recibe_correos")
        self.tree = ttk.Treeview(tabla_frame, columns=columnas, show="headings")

        for col, txt in [
            ("cliente_id", "ID"),
            ("tipo_cliente", "Tipo"),
            ("rut", "RUT"),
            ("nombre_mostrado", "Nombre / Razón Social"),
            ("email", "Email"),
            ("telefono", "Teléfono"),
            ("estado", "Activo"),
            ("recibe_correos", "Recibe"),
        ]:
            self.tree.heading(col, text=txt)

        self.tree.column("cliente_id", width=60, anchor="center")
        self.tree.column("tipo_cliente", width=90, anchor="center")
        self.tree.column("rut", width=120, anchor="w")
        self.tree.column("nombre_mostrado", width=240, anchor="w")
        self.tree.column("email", width=220, anchor="w")
        self.tree.column("telefono", width=120, anchor="w")
        self.tree.column("estado", width=70, anchor="center")
        self.tree.column("recibe_correos", width=70, anchor="center")

        sb = ttk.Scrollbar(tabla_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", lambda e: self.on_seleccionar_fila())

    def _ajustar_form_por_tipo(self):
        tipo = self.var_tipo.get()
        if tipo == "Corporativo":
            self.ent_nombres.configure(state="disabled")
            self.ent_apellidos.configure(state="disabled")
            self.ent_razon.configure(state="normal")
        else:
            self.ent_nombres.configure(state="normal")
            self.ent_apellidos.configure(state="normal")
            self.ent_razon.configure(state="disabled")

    def _leer_formulario(self) -> dict:
        return {
            "tipo_cliente": self.var_tipo.get(),
            "rut": self.var_rut.get(),
            "nombres": self.var_nombres.get(),
            "apellidos": self.var_apellidos.get(),
            "razon_social": self.var_razon.get(),
            "email": self.var_email.get(),
            "telefono": self.var_telefono.get(),
            "estado": self.var_estado.get(),
            "recibe_correos": self.var_recibe.get(),
            "observaciones": self.var_obs.get(),
        }

    def _limpiar_formulario(self):
        self.cliente_id_seleccionado = None
        self.var_tipo.set("Regular")
        self.var_rut.set("")
        self.var_nombres.set("")
        self.var_apellidos.set("")
        self.var_razon.set("")
        self.var_email.set("")
        self.var_telefono.set("")
        self.var_estado.set(1)
        self.var_recibe.set(1)
        self.var_obs.set("")
        self._ajustar_form_por_tipo()

    def _nombre_mostrado(self, r: dict) -> str:
        return str(r.get("razon_social") or (str(r.get("nombres", "")) + " " + str(r.get("apellidos", ""))).strip())

    def _aplicar_filtro_tipo(self, registros: list[dict]) -> list[dict]:
        tipo = self.var_filtro_tipo.get()
        if tipo == "Todos":
            return registros
        return [r for r in registros if str(r.get("tipo_cliente", "")) == tipo]

    def _cargar_tabla_clientes(self, registros: list[dict]):
        self.registros_actuales = []
        for item in self.tree.get_children():
            self.tree.delete(item)

        for r in registros:
            r2 = dict(r)
            r2["nombre_mostrado"] = self._nombre_mostrado(r2)
            self.tree.insert(
                "",
                "end",
                values=(
                    r2.get("cliente_id", ""),
                    r2.get("tipo_cliente", ""),
                    r2.get("rut", ""),
                    r2.get("nombre_mostrado", ""),
                    r2.get("email", ""),
                    r2.get("telefono", ""),
                    r2.get("estado", ""),
                    r2.get("recibe_correos", ""),
                ),
            )
            self.registros_actuales.append(r2)

    def _refrescar_listado_clientes(self):
        texto = self.var_buscar.get().strip()
        if texto:
            regs = buscar_clientes_por_nombre(texto)
        else:
            regs = listar_clientes()

        regs = self._aplicar_filtro_tipo(regs)
        self._cargar_tabla_clientes(regs)

        # También refrescamos la lista de clientes disponible para mensajería
        self._refrescar_lista_clientes_para_envio()

    # Eventos Clientes
    def on_buscar(self):
        self._refrescar_listado_clientes()
        registrar_evento("clientes", "BUSCAR", f"Texto='{self.var_buscar.get()}' Tipo='{self.var_filtro_tipo.get()}'")

    def on_ver_todo(self):
        self.var_buscar.set("")
        self.var_filtro_tipo.set("Todos")
        self._refrescar_listado_clientes()
        registrar_evento("clientes", "LISTAR", "Ver todo")

    def on_agregar(self):
        try:
            datos = self._leer_formulario()
            nuevo_id = crear_cliente(datos)
            registrar_evento("clientes", "CREAR", f"cliente_id={nuevo_id}")
            messagebox.showinfo("Éxito", "Cliente agregado correctamente.")
            self._refrescar_listado_clientes()
            self._limpiar_formulario()
        except Exception as e:
            registrar_evento("clientes", "CREAR_ERROR", str(e), "ERROR")
            messagebox.showerror("Error", str(e))

    def on_actualizar(self):
        if self.cliente_id_seleccionado is None:
            messagebox.showwarning("Atención", "Seleccione un cliente para actualizar.")
            return
        try:
            datos = self._leer_formulario()
            ok = actualizar_cliente(self.cliente_id_seleccionado, datos)
            if not ok:
                messagebox.showwarning("Atención", "No se pudo actualizar (no existe).")
                return
            registrar_evento("clientes", "ACTUALIZAR", f"cliente_id={self.cliente_id_seleccionado}")
            messagebox.showinfo("Éxito", "Cliente actualizado correctamente.")
            self._refrescar_listado_clientes()
            self._limpiar_formulario()
        except Exception as e:
            registrar_evento("clientes", "ACTUALIZAR_ERROR", str(e), "ERROR")
            messagebox.showerror("Error", str(e))

    def on_eliminar(self):
        if self.cliente_id_seleccionado is None:
            messagebox.showwarning("Atención", "Seleccione un cliente para eliminar.")
            return
        if not messagebox.askyesno("Confirmar", "¿Seguro que desea eliminar este cliente?"):
            return
        try:
            ok = eliminar_cliente(self.cliente_id_seleccionado)
            if ok:
                registrar_evento("clientes", "ELIMINAR", f"cliente_id={self.cliente_id_seleccionado}")
                messagebox.showinfo("Éxito", "Cliente eliminado.")
                self._refrescar_listado_clientes()
                self._limpiar_formulario()
            else:
                messagebox.showwarning("Atención", "No se pudo eliminar (no existe).")
        except Exception as e:
            registrar_evento("clientes", "ELIMINAR_ERROR", str(e), "ERROR")
            messagebox.showerror("Error", str(e))

    def on_limpiar(self):
        self._limpiar_formulario()

    def on_seleccionar_fila(self):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        if not vals:
            return
        cliente_id = int(vals[0])
        self.cliente_id_seleccionado = cliente_id
        r = obtener_cliente_por_id(cliente_id)
        if not r:
            return
        self.var_tipo.set(r.get("tipo_cliente", "Regular"))
        self.var_rut.set(r.get("rut", ""))
        self.var_nombres.set(r.get("nombres") or "")
        self.var_apellidos.set(r.get("apellidos") or "")
        self.var_razon.set(r.get("razon_social") or "")
        self.var_email.set(r.get("email") or "")
        self.var_telefono.set(r.get("telefono") or "")
        self.var_estado.set(int(r.get("estado", 1)))
        self.var_recibe.set(int(r.get("recibe_correos", 1)))
        self.var_obs.set(r.get("observaciones") or "")
        self._ajustar_form_por_tipo()

    def on_importar_excel(self):
        ruta = filedialog.askopenfilename(title="Seleccionar Excel", filetypes=[("Excel", "*.xlsx")])
        if not ruta:
            return

        modo = "actualizar"
        if not messagebox.askyesno("Importar", "Si el RUT existe, ¿actualizar? (Sí=actualiza / No=rechaza)"):
            modo = "rechazar"

        try:
            resumen = importar_clientes_excel(ruta, modo=modo)
            self._refrescar_listado_clientes()
            msg = (
                f"Importación finalizada.\n\n"
                f"Agregados: {resumen['agregados']}\n"
                f"Actualizados: {resumen['actualizados']}\n"
                f"Rechazados: {resumen['rechazados']}\n"
            )
            if resumen["errores"]:
                msg += "\nErrores (primeros 10):\n" + "\n".join(resumen["errores"][:10])
            messagebox.showinfo("Importación", msg)
        except Exception as e:
            registrar_evento("importacion", "ERROR", str(e), "ERROR")
            messagebox.showerror("Error", str(e))

    def on_exportar_excel(self):
        if not self.registros_actuales:
            messagebox.showwarning("Atención", "No hay datos para exportar.")
            return
        ruta = filedialog.asksaveasfilename(title="Guardar Excel", defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if not ruta:
            return
        try:
            exportar_clientes_excel(ruta, self.registros_actuales)
            messagebox.showinfo("Éxito", "Excel exportado correctamente.")
        except Exception as e:
            registrar_evento("exportacion", "EXCEL_ERROR", str(e), "ERROR")
            messagebox.showerror("Error", str(e))

    def on_exportar_pdf(self):
        if not self.registros_actuales:
            messagebox.showwarning("Atención", "No hay datos para exportar.")
            return
        ruta = filedialog.asksaveasfilename(title="Guardar PDF", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not ruta:
            return
        try:
            exportar_clientes_pdf(ruta, self.registros_actuales)
            messagebox.showinfo("Éxito", "PDF exportado correctamente.")
        except Exception as e:
            registrar_evento("exportacion", "PDF_ERROR", str(e), "ERROR")
            messagebox.showerror("Error", str(e))

    # =========================================================
    # PESTAÑA MENSAJERÍA
    # =========================================================

    def _crear_tab_mensajeria(self):
        cont = ttk.Frame(self.tab_mensajeria)
        cont.pack(fill="both", expand=True, padx=10, pady=10)

        cont.columnconfigure(0, weight=2)
        cont.columnconfigure(1, weight=2)
        cont.rowconfigure(0, weight=1)

        # --------------------------
        # Izquierda: Editor + plantillas
        # --------------------------
        izq = ttk.LabelFrame(cont, text="Carta / Plantillas")
        izq.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        izq.columnconfigure(1, weight=1)

        self.var_nombre_campana = tk.StringVar()
        self.var_asunto = tk.StringVar()

        r = 0
        ttk.Label(izq, text="Nombre campaña (opcional):").grid(row=r, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(izq, textvariable=self.var_nombre_campana).grid(row=r, column=1, sticky="ew", padx=8, pady=6)

        r += 1
        ttk.Label(izq, text="Asunto:").grid(row=r, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(izq, textvariable=self.var_asunto).grid(row=r, column=1, sticky="ew", padx=8, pady=6)

        r += 1
        ttk.Label(izq, text="Cuerpo (variables: {nombre} {apellidos} {razon_social} {rut}):").grid(
            row=r, column=0, columnspan=2, sticky="w", padx=8, pady=6
        )

        r += 1
        self.txt_cuerpo = tk.Text(izq, height=14, wrap="word")
        self.txt_cuerpo.grid(row=r, column=0, columnspan=2, sticky="nsew", padx=8, pady=6)
        izq.rowconfigure(r, weight=1)

        # Plantillas
        r += 1
        sep = ttk.Separator(izq, orient="horizontal")
        sep.grid(row=r, column=0, columnspan=2, sticky="ew", pady=8)

        r += 1
        ttk.Label(izq, text="Plantillas:").grid(row=r, column=0, sticky="w", padx=8)

        self.var_plantilla = tk.StringVar(value="")
        self.cmb_plantillas = ttk.Combobox(izq, textvariable=self.var_plantilla, state="readonly")
        self.cmb_plantillas.grid(row=r, column=1, sticky="ew", padx=8)
        self.cmb_plantillas.bind("<<ComboboxSelected>>", lambda e: self.on_cargar_plantilla())

        r += 1
        botones = ttk.Frame(izq)
        botones.grid(row=r, column=0, columnspan=2, sticky="ew", padx=8, pady=8)

        ttk.Button(botones, text="Guardar como plantilla", command=self.on_guardar_plantilla).pack(side="left", padx=4)
        ttk.Button(botones, text="Eliminar plantilla", command=self.on_eliminar_plantilla).pack(side="left", padx=4)
        ttk.Button(botones, text="Vista previa", command=self.on_vista_previa).pack(side="left", padx=4)

        # --------------------------
        # Derecha: selección destinatarios + envío
        # --------------------------
        der = ttk.LabelFrame(cont, text="Destinatarios y Envío")
        der.grid(row=0, column=1, sticky="nsew")
        der.columnconfigure(0, weight=1)
        der.rowconfigure(4, weight=1)

        # Selección por tipo_cliente
        self.var_usar_tipo = tk.IntVar(value=1)
        self.var_tipo_envio = tk.StringVar(value="Todos")

        ttk.Checkbutton(der, text="Enviar por tipo_cliente", variable=self.var_usar_tipo).grid(
            row=0, column=0, sticky="w", padx=8, pady=6
        )

        fila_tipo = ttk.Frame(der)
        fila_tipo.grid(row=1, column=0, sticky="ew", padx=8)
        ttk.Label(fila_tipo, text="Tipo:").pack(side="left")
        cmb = ttk.Combobox(
            fila_tipo,
            textvariable=self.var_tipo_envio,
            values=["Todos", "Regular", "Premium", "Corporativo"],
            state="readonly",
            width=18,
        )
        cmb.pack(side="left", padx=8)

        # Selección manual
        self.var_usar_manual = tk.IntVar(value=0)
        ttk.Checkbutton(der, text="Agregar clientes específicos (selección manual)", variable=self.var_usar_manual).grid(
            row=2, column=0, sticky="w", padx=8, pady=6
        )

        # Buscador en lista manual
        fila_busca = ttk.Frame(der)
        fila_busca.grid(row=3, column=0, sticky="ew", padx=8)
        ttk.Label(fila_busca, text="Buscar en lista:").pack(side="left")
        self.var_buscar_envio = tk.StringVar()
        ent = ttk.Entry(fila_busca, textvariable=self.var_buscar_envio, width=25)
        ent.pack(side="left", padx=8)
        ent.bind("<Return>", lambda e: self._refrescar_lista_clientes_para_envio())
        ttk.Button(fila_busca, text="Filtrar", command=self._refrescar_lista_clientes_para_envio).pack(side="left")

        # Lista manual (Treeview)
        self.tree_envio = ttk.Treeview(
            der,
            columns=("id", "tipo", "rut", "nombre", "email"),
            show="headings",
            selectmode="extended",
        )
        self.tree_envio.heading("id", text="ID")
        self.tree_envio.heading("tipo", text="Tipo")
        self.tree_envio.heading("rut", text="RUT")
        self.tree_envio.heading("nombre", text="Nombre")
        self.tree_envio.heading("email", text="Email")

        self.tree_envio.column("id", width=50, anchor="center")
        self.tree_envio.column("tipo", width=90, anchor="center")
        self.tree_envio.column("rut", width=110, anchor="w")
        self.tree_envio.column("nombre", width=200, anchor="w")
        self.tree_envio.column("email", width=220, anchor="w")

        sb = ttk.Scrollbar(der, orient="vertical", command=self.tree_envio.yview)
        self.tree_envio.configure(yscrollcommand=sb.set)

        self.tree_envio.grid(row=4, column=0, sticky="nsew", padx=8, pady=6)
        sb.grid(row=4, column=1, sticky="ns")

        # Botón enviar + progreso
        fila_envio = ttk.Frame(der)
        fila_envio.grid(row=5, column=0, sticky="ew", padx=8, pady=10)
        fila_envio.columnconfigure(1, weight=1)

        self.btn_enviar = ttk.Button(fila_envio, text="ENVIAR CAMPAÑA", command=self.on_enviar_campana)
        self.btn_enviar.grid(row=0, column=0, padx=4)

        self.pb = ttk.Progressbar(fila_envio, mode="determinate")
        self.pb.grid(row=0, column=1, sticky="ew", padx=6)

        self.lbl_estado_envio = ttk.Label(fila_envio, text="Listo.")
        self.lbl_estado_envio.grid(row=1, column=0, columnspan=2, sticky="w", pady=4)

    def _refrescar_listado_plantillas(self):
        """Carga plantillas en combobox."""
        pls = listar_plantillas(incluir_inactivas=False)
        # Guardamos mapa nombre -> id para usarlo después
        self._plantillas_map = {p["nombre"]: int(p["plantilla_id"]) for p in pls}
        self.cmb_plantillas["values"] = [""] + list(self._plantillas_map.keys())
        self.var_plantilla.set("")

    def on_guardar_plantilla(self):
        """Guardar plantilla con nombre pedido al usuario."""
        nombre = self.var_plantilla.get().strip()
        if not nombre:
            # si no hay seleccionado, pedimos nombre simple
            nombre = simple_input(self, "Nombre de plantilla", "Ingrese nombre para guardar la plantilla:")
            if not nombre:
                return
        asunto = self.var_asunto.get().strip()
        cuerpo = self.txt_cuerpo.get("1.0", tk.END).strip()

        try:
            # Si existe nombre, actualizamos; si no, creamos
            pid = self._plantillas_map.get(nombre)
            if pid:
                actualizar_plantilla(pid, nombre, asunto, cuerpo, activa=1)
            else:
                crear_plantilla(nombre, asunto, cuerpo, activa=1)

            self._refrescar_listado_plantillas()
            self.var_plantilla.set(nombre)
            messagebox.showinfo("Plantilla", "Plantilla guardada correctamente.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def on_cargar_plantilla(self):
        """Carga asunto y cuerpo desde plantilla seleccionada."""
        nombre = self.var_plantilla.get().strip()
        if not nombre:
            return
        pid = self._plantillas_map.get(nombre)
        if not pid:
            return
        p = obtener_plantilla_por_id(pid)
        if not p:
            return
        self.var_asunto.set(p.get("asunto", ""))
        self.txt_cuerpo.delete("1.0", tk.END)
        self.txt_cuerpo.insert("1.0", p.get("cuerpo", ""))

    def on_eliminar_plantilla(self):
        """Elimina plantilla seleccionada."""
        nombre = self.var_plantilla.get().strip()
        if not nombre:
            messagebox.showwarning("Atención", "Seleccione una plantilla.")
            return
        pid = self._plantillas_map.get(nombre)
        if not pid:
            return
        if not messagebox.askyesno("Confirmar", f"¿Eliminar plantilla '{nombre}'?"):
            return
        eliminar_plantilla(pid)
        self._refrescar_listado_plantillas()
        messagebox.showinfo("Plantilla", "Plantilla eliminada.")

    def _refrescar_lista_clientes_para_envio(self):
        """Carga la lista de clientes para selección manual."""
        texto = self.var_buscar_envio.get().strip().casefold() if hasattr(self, "var_buscar_envio") else ""
        clientes = listar_clientes()

        # Filtrado simple por texto
        if texto:
            filtrados = []
            for c in clientes:
                nombre = self._nombre_mostrado(c).casefold()
                rut = str(c.get("rut", "")).casefold()
                email = str(c.get("email", "")).casefold()
                if texto in nombre or texto in rut or texto in email:
                    filtrados.append(c)
            clientes = filtrados

        # Limpiamos tree
        if hasattr(self, "tree_envio"):
            for item in self.tree_envio.get_children():
                self.tree_envio.delete(item)

            for c in clientes:
                self.tree_envio.insert(
                    "",
                    "end",
                    values=(
                        c.get("cliente_id", ""),
                        c.get("tipo_cliente", ""),
                        c.get("rut", ""),
                        self._nombre_mostrado(c),
                        c.get("email") or "",
                    ),
                )

    def _obtener_clientes_seleccion_manual(self) -> list[int]:
        """Devuelve IDs de clientes seleccionados manualmente."""
        ids = []
        for item in self.tree_envio.selection():
            vals = self.tree_envio.item(item, "values")
            if vals:
                ids.append(int(vals[0]))
        return ids

    def on_vista_previa(self):
        """Muestra vista previa usando el primer cliente seleccionado (si hay)."""
        asunto = self.var_asunto.get().strip()
        cuerpo = self.txt_cuerpo.get("1.0", tk.END).strip()
        if not asunto or not cuerpo:
            messagebox.showwarning("Atención", "Debe escribir asunto y cuerpo.")
            return

        # Intentamos tomar un cliente de selección manual; si no, buscamos uno del tipo seleccionado
        cliente_demo = None
        ids = self._obtener_clientes_seleccion_manual()
        if ids:
            cliente_demo = obtener_cliente_por_id(ids[0])
        else:
            tipo = self.var_tipo_envio.get()
            todos = listar_clientes()
            for c in todos:
                if tipo == "Todos" or c.get("tipo_cliente") == tipo:
                    cliente_demo = c
                    break

        if not cliente_demo:
            messagebox.showwarning("Atención", "No hay cliente disponible para vista previa.")
            return

        asunto_r = renderizar(asunto, cliente_demo)
        cuerpo_r = renderizar(cuerpo, cliente_demo)

        messagebox.showinfo("Vista previa", f"Asunto:\n{asunto_r}\n\nCuerpo:\n{cuerpo_r}")

    def _construir_destinatarios(self) -> list[dict]:
        """
        Construye la lista final de clientes (sin duplicados) según:
          - Envío por tipo_cliente (si está marcado)
          - Selección manual (si está marcado)
        """
        clientes = listar_clientes()
        destino = {}

        # 1) Por tipo_cliente
        if self.var_usar_tipo.get() == 1:
            tipo = self.var_tipo_envio.get()
            for c in clientes:
                if tipo == "Todos" or c.get("tipo_cliente") == tipo:
                    destino[int(c["cliente_id"])] = c

        # 2) Manual
        if self.var_usar_manual.get() == 1:
            ids_manual = set(self._obtener_clientes_seleccion_manual())
            for c in clientes:
                if int(c["cliente_id"]) in ids_manual:
                    destino[int(c["cliente_id"])] = c

        return list(destino.values())

    def on_enviar_campana(self):
        """Crea campaña + detalle + envía en thread."""
        if self.envio_en_proceso:
            messagebox.showwarning("Atención", "Ya hay un envío en proceso.")
            return

        # Validar config correo
        self.config_correo = cargar_config_correo()
        ok, msg = config_es_valida(self.config_correo)
        if not ok:
            messagebox.showwarning("Configuración Gmail", msg + "\n\nVaya a la pestaña Configuración y guarde el correo.")
            return

        nombre = self.var_nombre_campana.get().strip()
        asunto = self.var_asunto.get().strip()
        cuerpo = self.txt_cuerpo.get("1.0", tk.END).strip()

        if not asunto or not cuerpo:
            messagebox.showwarning("Atención", "Debe escribir asunto y cuerpo.")
            return

        destinatarios = self._construir_destinatarios()
        if not destinatarios:
            messagebox.showwarning("Atención", "No hay destinatarios seleccionados.")
            return

        # Guardamos criterio usado en JSON (auditoría)
        criterio = {
            "usar_tipo": int(self.var_usar_tipo.get()),
            "tipo": self.var_tipo_envio.get(),
            "usar_manual": int(self.var_usar_manual.get()),
            "manual_ids": self._obtener_clientes_seleccion_manual(),
        }
        criterio_json = json.dumps(criterio, ensure_ascii=False)

        # 1) Crear campaña
        campana_id = crear_campana(nombre, asunto, cuerpo, criterio_json)

        # 2) Crear detalle de envíos (PENDIENTE/OMITIDO)
        total, pendientes, omitidos = crear_detalle_envios(campana_id, destinatarios)

        # Inicializamos progreso
        self.pb["value"] = 0
        self.pb["maximum"] = max(pendientes, 1)
        self.lbl_estado_envio.config(text=f"Campaña {campana_id}: Pendientes={pendientes} Omitidos={omitidos}")
        self.btn_enviar.config(state="disabled")

        # 3) Lanzar thread de envío
        self.envio_en_proceso = True

        self.hilo_envio = threading.Thread(
            target=self._hilo_enviar_campana,
            args=(campana_id, asunto, cuerpo, destinatarios),
            daemon=True,
        )
        self.hilo_envio.start()

        # 4) Empezar a procesar cola de eventos del hilo
        self.after(100, self._procesar_cola_envio)

    def _hilo_enviar_campana(self, campana_id: int, asunto: str, cuerpo: str, destinatarios: list[dict]):
        """
        Hilo de envío real:
          - Obtiene pendientes
          - Envía uno por uno
          - Actualiza envios_detalle
          - Va reportando progreso a la cola
        """
        # Mapa cliente_id -> cliente (para personalizar sin consultar DB cada vez)
        mapa_clientes = {int(c["cliente_id"]): c for c in destinatarios}

        pendientes = listar_envios_pendientes(campana_id)
        enviados_ok = 0
        fallidos = 0
        procesados = 0

        for envio in pendientes:
            envio_id = int(envio["envio_id"])
            cliente_id = envio.get("cliente_id")
            email = envio.get("email_destino")

            cliente = mapa_clientes.get(int(cliente_id)) if cliente_id is not None else {}

            # Renderizar asunto/cuerpo por cliente (personalización)
            asunto_r = renderizar(asunto, cliente)
            cuerpo_r = renderizar(cuerpo, cliente)

            try:
                enviar_correo(email, asunto_r, cuerpo_r, config=self.config_correo)
                marcar_envio_enviado(envio_id)
                enviados_ok += 1
            except Exception as e:
                marcar_envio_error(envio_id, str(e))
                fallidos += 1

            procesados += 1

            # Enviamos progreso a la cola (para UI)
            self.cola_envio.put(("PROGRESO", procesados, enviados_ok, fallidos))

        # Al finalizar, actualizamos resumen campaña
        total, enviados, fallidos2 = contar_estados(campana_id)
        actualizar_resumen_campana(campana_id, total, enviados, fallidos2)

        # Notificamos fin
        self.cola_envio.put(("FIN", campana_id, total, enviados, fallidos2))

    def _procesar_cola_envio(self):
        """
        Procesa mensajes del hilo en la UI.
        Se llama con after() repetidamente hasta que termine.
        """
        while not self.cola_envio.empty():
            msg = self.cola_envio.get()

            if msg[0] == "PROGRESO":
                _, procesados, ok, err = msg
                self.pb["value"] = procesados
                self.lbl_estado_envio.config(text=f"Enviando... Procesados={procesados} OK={ok} ERROR={err}")

            elif msg[0] == "FIN":
                _, campana_id, total, enviados, fallidos = msg
                self.envio_en_proceso = False
                self.btn_enviar.config(state="normal")
                self.lbl_estado_envio.config(text=f"Finalizado campaña {campana_id}: Total={total} Enviados={enviados} Fallidos={fallidos}")
                messagebox.showinfo("Envío finalizado", f"Campaña {campana_id}\nTotal={total}\nEnviados={enviados}\nFallidos={fallidos}")

                # Refrescar historial
                self._refrescar_listado_campanas()

        if self.envio_en_proceso:
            self.after(150, self._procesar_cola_envio)

    # =========================================================
    # PESTAÑA HISTORIAL
    # =========================================================

    def _crear_tab_historial(self):
        cont = ttk.Frame(self.tab_historial)
        cont.pack(fill="both", expand=True, padx=10, pady=10)

        cont.columnconfigure(0, weight=1)
        cont.columnconfigure(1, weight=2)
        cont.rowconfigure(0, weight=1)

        # Campañas
        frm_c = ttk.LabelFrame(cont, text="Campañas")
        frm_c.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        frm_c.rowconfigure(1, weight=1)
        frm_c.columnconfigure(0, weight=1)

        ttk.Button(frm_c, text="Recargar", command=self._refrescar_listado_campanas).grid(row=0, column=0, sticky="w", padx=8, pady=6)

        self.tree_camp = ttk.Treeview(frm_c, columns=("id", "asunto", "total", "enviados", "fallidos", "fecha"), show="headings")
        for col, txt in [
            ("id", "ID"),
            ("asunto", "Asunto"),
            ("total", "Total"),
            ("enviados", "Enviados"),
            ("fallidos", "Fallidos"),
            ("fecha", "Fecha"),
        ]:
            self.tree_camp.heading(col, text=txt)

        self.tree_camp.column("id", width=60, anchor="center")
        self.tree_camp.column("asunto", width=220, anchor="w")
        self.tree_camp.column("total", width=70, anchor="center")
        self.tree_camp.column("enviados", width=80, anchor="center")
        self.tree_camp.column("fallidos", width=80, anchor="center")
        self.tree_camp.column("fecha", width=150, anchor="w")

        sb1 = ttk.Scrollbar(frm_c, orient="vertical", command=self.tree_camp.yview)
        self.tree_camp.configure(yscrollcommand=sb1.set)

        self.tree_camp.grid(row=1, column=0, sticky="nsew", padx=8, pady=6)
        sb1.grid(row=1, column=1, sticky="ns")

        self.tree_camp.bind("<<TreeviewSelect>>", lambda e: self._cargar_detalle_campana())

        # Detalle
        frm_d = ttk.LabelFrame(cont, text="Detalle de envíos")
        frm_d.grid(row=0, column=1, sticky="nsew")
        frm_d.rowconfigure(0, weight=1)
        frm_d.columnconfigure(0, weight=1)

        self.tree_det = ttk.Treeview(frm_d, columns=("envio_id", "cliente_id", "email", "estado", "error", "enviado_en"), show="headings")
        for col, txt in [
            ("envio_id", "EnvioID"),
            ("cliente_id", "ClienteID"),
            ("email", "Email"),
            ("estado", "Estado"),
            ("error", "Error/Motivo"),
            ("enviado_en", "Fecha"),
        ]:
            self.tree_det.heading(col, text=txt)

        self.tree_det.column("envio_id", width=70, anchor="center")
        self.tree_det.column("cliente_id", width=80, anchor="center")
        self.tree_det.column("email", width=220, anchor="w")
        self.tree_det.column("estado", width=90, anchor="center")
        self.tree_det.column("error", width=260, anchor="w")
        self.tree_det.column("enviado_en", width=150, anchor="w")

        sb2 = ttk.Scrollbar(frm_d, orient="vertical", command=self.tree_det.yview)
        self.tree_det.configure(yscrollcommand=sb2.set)

        self.tree_det.grid(row=0, column=0, sticky="nsew", padx=8, pady=6)
        sb2.grid(row=0, column=1, sticky="ns")

    def _refrescar_listado_campanas(self):
        """Recarga campañas en historial."""
        self._refrescar_listado_campanas()
        self._refrescar_listado_plantillas()

    def _refrescar_listado_campanas(self):
        if not hasattr(self, "tree_camp"):
            return
        for item in self.tree_camp.get_children():
            self.tree_camp.delete(item)

        for c in listar_campanas():
            self.tree_camp.insert(
                "",
                "end",
                values=(
                    c.get("campana_id", ""),
                    c.get("asunto", "")[:40],
                    c.get("total_destinatarios", 0),
                    c.get("enviados", 0),
                    c.get("fallidos", 0),
                    c.get("creada_en", ""),
                ),
            )

        # Limpiar detalle
        if hasattr(self, "tree_det"):
            for item in self.tree_det.get_children():
                self.tree_det.delete(item)

    def _cargar_detalle_campana(self):
        """Carga detalle de envíos de la campaña seleccionada."""
        sel = self.tree_camp.selection()
        if not sel:
            return
        vals = self.tree_camp.item(sel[0], "values")
        if not vals:
            return
        campana_id = int(vals[0])

        for item in self.tree_det.get_children():
            self.tree_det.delete(item)

        for e in listar_envios_por_campana(campana_id):
            self.tree_det.insert(
                "",
                "end",
                values=(
                    e.get("envio_id", ""),
                    e.get("cliente_id", ""),
                    e.get("email_destino", ""),
                    e.get("estado", ""),
                    e.get("error_mensaje", "") or "",
                    e.get("enviado_en", "") or "",
                ),
            )

    # =========================================================
    # PESTAÑA CONFIG (Gmail)
    # =========================================================

    def _crear_tab_config(self):
        frm = ttk.LabelFrame(self.tab_config, text="Configuración Gmail (SMTP)")
        frm.pack(fill="x", padx=10, pady=10)

        frm.columnconfigure(1, weight=1)

        self.var_cfg_correo = tk.StringVar()
        self.var_cfg_app_pass = tk.StringVar()
        self.var_cfg_nombre = tk.StringVar()
        self.var_cfg_prueba = tk.StringVar()

        r = 0
        ttk.Label(frm, text="Correo Gmail (remitente):").grid(row=r, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(frm, textvariable=self.var_cfg_correo).grid(row=r, column=1, sticky="ew", padx=8, pady=6)

        r += 1
        ttk.Label(frm, text="Contraseña de aplicación (App Password):").grid(row=r, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(frm, textvariable=self.var_cfg_app_pass, show="*").grid(row=r, column=1, sticky="ew", padx=8, pady=6)

        r += 1
        ttk.Label(frm, text="Nombre remitente (opcional):").grid(row=r, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(frm, textvariable=self.var_cfg_nombre).grid(row=r, column=1, sticky="ew", padx=8, pady=6)

        r += 1
        ttk.Separator(frm, orient="horizontal").grid(row=r, column=0, columnspan=2, sticky="ew", pady=10)

        r += 1
        ttk.Label(frm, text="Enviar prueba a:").grid(row=r, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(frm, textvariable=self.var_cfg_prueba).grid(row=r, column=1, sticky="ew", padx=8, pady=6)

        r += 1
        botones = ttk.Frame(frm)
        botones.grid(row=r, column=0, columnspan=2, sticky="w", padx=8, pady=10)

        ttk.Button(botones, text="Guardar configuración", command=self.on_guardar_config).pack(side="left", padx=4)
        ttk.Button(botones, text="Probar envío", command=self.on_probar_envio).pack(side="left", padx=4)

        self.lbl_cfg_estado = ttk.Label(frm, text="Estado: (sin validar)")
        self.lbl_cfg_estado.grid(row=r + 1, column=0, columnspan=2, sticky="w", padx=8, pady=6)

    def _cargar_config_en_form(self):
        """Carga config del archivo a la UI."""
        cfg = self.config_correo or {}
        self.var_cfg_correo.set(cfg.get("correo", ""))
        self.var_cfg_app_pass.set(cfg.get("app_password", ""))
        self.var_cfg_nombre.set(cfg.get("nombre_remitente", ""))
        ok, msg = config_es_valida(cfg)
        self.lbl_cfg_estado.config(text=f"Estado: {'OK' if ok else msg}")

    def on_guardar_config(self):
        """Guarda config en AppData/correo.json."""
        cfg = {
            "correo": self.var_cfg_correo.get().strip(),
            "app_password": self.var_cfg_app_pass.get().strip(),
            "nombre_remitente": self.var_cfg_nombre.get().strip(),
        }
        ok, msg = config_es_valida(cfg)
        if not ok:
            messagebox.showwarning("Config", msg)
            return
        guardar_config_correo(cfg)
        self.config_correo = cfg
        self.lbl_cfg_estado.config(text="Estado: OK (guardado)")
        messagebox.showinfo("Config", "Configuración guardada correctamente.")

    def on_probar_envio(self):
        """Envía correo de prueba."""
        destino = self.var_cfg_prueba.get().strip()
        if not destino:
            messagebox.showwarning("Prueba", "Ingrese un email de destino para la prueba.")
            return
        try:
            # Aseguramos que esté guardada y válida
            self.on_guardar_config()
            probar_envio(destino)
            messagebox.showinfo("Prueba", "Correo de prueba enviado correctamente.")
        except Exception as e:
            messagebox.showerror("Prueba", str(e))


# ------------------------------------------------------------
# Helper: input simple (sin usar librerías externas)
# ------------------------------------------------------------

def simple_input(parent, titulo: str, texto: str) -> str:
    """
    Ventana pequeña para pedir texto al usuario.
    Retorna string o "" si canceló.
    """
    win = tk.Toplevel(parent)
    win.title(titulo)
    win.transient(parent)
    win.grab_set()

    tk.Label(win, text=texto).pack(padx=10, pady=8)
    var = tk.StringVar()
    ent = ttk.Entry(win, textvariable=var, width=40)
    ent.pack(padx=10, pady=6)
    ent.focus_set()

    resp = {"v": ""}

    def ok():
        resp["v"] = var.get().strip()
        win.destroy()

    def cancel():
        resp["v"] = ""
        win.destroy()

    btns = ttk.Frame(win)
    btns.pack(pady=8)
    ttk.Button(btns, text="OK", command=ok).pack(side="left", padx=5)
    ttk.Button(btns, text="Cancelar", command=cancel).pack(side="left", padx=5)

    win.wait_window()
    return resp["v"]
