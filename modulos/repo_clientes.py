# ============================================
# Archivo: modulos/repo_clientes.py
# Propósito:
#   - CRUD de clientes usando SQLite
#   - Buscador por nombre (y además por RUT/email)
#   - Funciones extra para importación por rut_normalizado
# ============================================

from __future__ import annotations  # Permite tipos modernos
from typing import Any, Dict, List, Optional  # Tipos para claridad

from .bd_sqlite import obtener_conexion  # Conexión a SQLite
from .validaciones import (
    validar_y_preparar_cliente,  # Valida y construye dict listo para DB
    normalizar_texto,            # Limpia textos
    rut_a_normalizado,           # Normaliza rut para comparar
)


def _fila_a_dict(fila) -> Dict[str, Any]:
    """
    Convierte sqlite3.Row a dict normal.
    Esto facilita usar los resultados en UI y exportaciones.
    """
    return dict(fila) if fila is not None else {}


# =========================================================
# Funciones auxiliares para importación / búsqueda por RUT
# =========================================================

def obtener_cliente_por_rut_normalizado(rut_normalizado: str) -> Optional[Dict[str, Any]]:
    """
    Busca un cliente por rut_normalizado (clave única en DB).
    Retorna dict si existe, o None si no existe.
    """
    rut_norm = rut_a_normalizado(rut_normalizado)  # Asegura formato comparable
    if not rut_norm:
        return None

    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM clientes WHERE rut_normalizado = ?", (rut_norm,))
        fila = cur.fetchone()
        return _fila_a_dict(fila) if fila else None
    finally:
        conn.close()


def obtener_cliente_id_por_rut_normalizado(rut_normalizado: str) -> Optional[int]:
    """
    Devuelve solo el cliente_id si existe un cliente con ese rut_normalizado.
    Es útil para importar Excel (decidir crear o actualizar).
    """
    cli = obtener_cliente_por_rut_normalizado(rut_normalizado)
    if not cli:
        return None
    return int(cli["cliente_id"])


# =========================================================
# Crear (INSERT)
# =========================================================

def crear_cliente(datos: Dict[str, Any]) -> int:
    """
    Crea un cliente en la base de datos.

    - Valida y prepara datos (incluye rut_normalizado, nombre_busqueda).
    - Inserta en SQLite.
    - Retorna el cliente_id creado.

    Si hay error de validación, lanza ValueError con el detalle.
    """
    ok, cliente, errores = validar_y_preparar_cliente(datos)  # Validación principal
    if not ok:
        raise ValueError("No se puede crear cliente:\n- " + "\n- ".join(errores))

    conn = obtener_conexion()  # Abrimos conexión a la BD
    try:
        cur = conn.cursor()  # Cursor para ejecutar SQL

        cur.execute(
            """
            INSERT INTO clientes (
                tipo_cliente, rut, rut_normalizado,
                nombres, apellidos, razon_social,
                email, telefono,
                recibe_correos, estado,
                nombre_busqueda, observaciones
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cliente["tipo_cliente"],
                cliente["rut"],
                cliente["rut_normalizado"],
                cliente["nombres"],
                cliente["apellidos"],
                cliente["razon_social"],
                cliente["email"],
                cliente["telefono"],
                cliente["recibe_correos"],
                cliente["estado"],
                cliente["nombre_busqueda"],
                cliente["observaciones"],
            ),
        )

        conn.commit()  # Confirmamos cambios
        return int(cur.lastrowid)  # ID del registro insertado

    finally:
        conn.close()  # Cerramos conexión


# =========================================================
# Read (SELECT)
# =========================================================

def obtener_cliente_por_id(cliente_id: int) -> Optional[Dict[str, Any]]:
    """
    Devuelve un cliente por su ID interno.
    Si no existe, devuelve None.
    """
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM clientes WHERE cliente_id = ?", (cliente_id,))
        fila = cur.fetchone()
        return _fila_a_dict(fila) if fila else None
    finally:
        conn.close()


def listar_clientes() -> List[Dict[str, Any]]:
    """
    Devuelve todos los clientes ordenados por fecha_registro (desc).
    """
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM clientes ORDER BY fecha_registro DESC")
        filas = cur.fetchall()
        return [_fila_a_dict(f) for f in filas]
    finally:
        conn.close()


# =========================================================
# Buscar (por nombre/RUT/email)
# =========================================================

def buscar_clientes_por_nombre(texto: str) -> List[Dict[str, Any]]:
    """
    Buscador principal:
    - Busca por nombre_busqueda (contiene)
    - Busca por rut_normalizado (si el usuario escribe rut con o sin formato)
    - Busca por email

    Si texto está vacío, retorna todos.
    """
    q = normalizar_texto(texto).casefold()  # Normaliza texto (minúsculas)
    if not q:
        return listar_clientes()

    rut_like = rut_a_normalizado(q)  # Si el usuario escribe un RUT, lo normalizamos

    conn = obtener_conexion()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT *
            FROM clientes
            WHERE nombre_busqueda LIKE ?
               OR rut_normalizado LIKE ?
               OR COALESCE(email,'') LIKE ?
            ORDER BY fecha_registro DESC
            """,
            (f"%{q}%", f"%{rut_like}%", f"%{q}%"),
        )

        filas = cur.fetchall()
        return [_fila_a_dict(f) for f in filas]

    finally:
        conn.close()


# =========================================================
# Update (UPDATE)
# =========================================================

def actualizar_cliente(cliente_id: int, datos: Dict[str, Any]) -> bool:
    """
    Actualiza un cliente por cliente_id.

    - Valida datos igual que en crear.
    - Si el cliente no existe, retorna False.
    - Si actualiza, retorna True.
    """
    existente = obtener_cliente_por_id(cliente_id)  # Verificamos que exista
    if not existente:
        return False

    ok, cliente, errores = validar_y_preparar_cliente(datos)  # Validamos datos
    if not ok:
        raise ValueError("No se puede actualizar cliente:\n- " + "\n- ".join(errores))

    conn = obtener_conexion()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE clientes
            SET
                tipo_cliente = ?,
                rut = ?,
                rut_normalizado = ?,
                nombres = ?,
                apellidos = ?,
                razon_social = ?,
                email = ?,
                telefono = ?,
                recibe_correos = ?,
                estado = ?,
                nombre_busqueda = ?,
                observaciones = ?
            WHERE cliente_id = ?
            """,
            (
                cliente["tipo_cliente"],
                cliente["rut"],
                cliente["rut_normalizado"],
                cliente["nombres"],
                cliente["apellidos"],
                cliente["razon_social"],
                cliente["email"],
                cliente["telefono"],
                cliente["recibe_correos"],
                cliente["estado"],
                cliente["nombre_busqueda"],
                cliente["observaciones"],
                cliente_id,
            ),
        )

        conn.commit()
        return cur.rowcount > 0  # True si actualizó una fila

    finally:
        conn.close()


# =========================================================
# Delete (DELETE)
# =========================================================

def eliminar_cliente(cliente_id: int) -> bool:
    """
    Elimina un cliente por cliente_id.
    Retorna True si eliminó algo, False si no existía.
    """
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM clientes WHERE cliente_id = ?", (cliente_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
