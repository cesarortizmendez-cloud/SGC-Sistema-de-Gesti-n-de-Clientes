# ============================================
# Archivo: modulos/exportaciones.py
# Propósito:
#   - Exportar listas de clientes a Excel y PDF
#   - Se usa desde UI (exporta lo que esté visible/filtrado)
# ============================================

from __future__ import annotations
from typing import Any, Dict, List

from openpyxl import Workbook  # Crear Excel
from reportlab.lib.pagesizes import A4  # Tamaño hoja PDF
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer  # PDF
from reportlab.lib import colors  # Estilos PDF
from reportlab.lib.styles import getSampleStyleSheet  # Estilos texto

from .repo_logs import registrar_evento


def exportar_clientes_excel(ruta_xlsx: str, registros: List[Dict[str, Any]]) -> None:
    """
    Exporta clientes a Excel.
    registros: lista de dicts (por ejemplo lo que la UI tiene cargado en la tabla).
    """
    registrar_evento("exportacion", "EXCEL", f"Exportando {len(registros)} clientes a {ruta_xlsx}")

    wb = Workbook()              # Crea un libro Excel
    ws = wb.active               # Hoja activa
    ws.title = "Clientes"        # Nombre de la hoja

    # Definimos columnas a exportar (orden fijo y claro)
    columnas = [
        ("cliente_id", "ID"),
        ("tipo_cliente", "Tipo"),
        ("rut", "RUT"),
        ("nombre_mostrado", "Nombre/Razón Social"),
        ("email", "Email"),
        ("telefono", "Teléfono"),
        ("estado", "Estado(1/0)"),
        ("recibe_correos", "RecibeCorreos(1/0)"),
        ("fecha_registro", "FechaRegistro"),
    ]

    # Escribimos encabezados
    ws.append([titulo for _, titulo in columnas])

    # Escribimos filas
    for r in registros:
        ws.append([r.get(clave, "") for clave, _ in columnas])

    wb.save(ruta_xlsx)  # Guarda archivo


def exportar_clientes_pdf(ruta_pdf: str, registros: List[Dict[str, Any]]) -> None:
    """
    Exporta clientes a PDF con una tabla simple.
    """
    registrar_evento("exportacion", "PDF", f"Exportando {len(registros)} clientes a {ruta_pdf}")

    doc = SimpleDocTemplate(ruta_pdf, pagesize=A4)  # Documento PDF
    styles = getSampleStyleSheet()                  # Estilos por defecto

    elementos = []  # Lista de elementos a imprimir en el PDF

    # Título
    elementos.append(Paragraph("Reporte de Clientes", styles["Title"]))
    elementos.append(Spacer(1, 12))

    # Encabezados y filas de la tabla
    encabezados = ["ID", "Tipo", "RUT", "Nombre/Razón Social", "Email", "Teléfono", "Estado", "RecibeCorreos"]
    data = [encabezados]

    for r in registros:
        fila = [
            str(r.get("cliente_id", "")),
            str(r.get("tipo_cliente", "")),
            str(r.get("rut", "")),
            str(r.get("nombre_mostrado", "")),
            str(r.get("email", "")),
            str(r.get("telefono", "")),
            str(r.get("estado", "")),
            str(r.get("recibe_correos", "")),
        ]
        data.append(fila)

    tabla = Table(data, repeatRows=1)  # repeatRows=1 repite encabezado si hay varias páginas

    # Estilo básico (rejilla + encabezado)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )

    elementos.append(tabla)
    doc.build(elementos)  # Genera el PDF
