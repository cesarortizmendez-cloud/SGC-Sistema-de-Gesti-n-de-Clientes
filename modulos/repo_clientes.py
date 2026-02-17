# ============================================
# Archivo: modulos/repo_clientes.py
# Propósito:
#   - CRUD de clientes usando SQLite
#   - Buscador por nombre (y además por RUT/email como extra útil)
# ============================================

from __future__ import annotations  # Para usar tipos modernos
from typing import Any, Dict, List, Optional  # Tipos para claridad

from .bd_sqlite import obtener_conexion  # Conexión a SQLite
from .validaciones import validar_y_preparar_cliente, normalizar_texto, rut_a_normalizado  # Validación y utilidades


def _fila_a_dict(fila) -> Dict[str, Any]:
    """
    Convierte sqlite3.Row a dict normal.
    Esto es útil para devolver datos “limpios” al resto del sistema (UI, exportaciones).
    """
    return dict(fila) if fila is not None else {}


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
    ok, cliente, errores = validar_y_preparar_cliente(datos)
    if not ok:
        raise ValueError("No se puede crear cliente:\n- " + "\n- ".join(errores))

    conn = obtener_conexion()
    try:
        cur = conn.cursor()

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

        conn.commit()
        return int(cur.lastrowid)

    finally:
        conn.close()


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
    Buscador principal (lo que pediste):
    - Busca por nombre_busqueda (contiene)
    - Además busca por rut_normalizado (si el usuario escribe números)
    - Además busca por email (por si escribe una parte del correo)

    Si texto está vacío, retorna todos.
    """
    q = normalizar_texto(texto).casefold()
    if not q:
        return listar_clientes()

    # También preparamos una versión “rut-like” por si el usuario escribe rut con puntos/guion
    rut_like = rut_a_normalizado(q)

    conn = obtener_conexion()
    try:
        cur = conn.cursor()

        # Usamos LIKE con % para “contiene”
        # Nota: nombre_busqueda se guarda en minúsculas, por eso comparamos con q casefold.
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

    - Valida datos igual que en crear (incluye RUT).
    - Si el cliente no existe, retorna False.
    - Si actualiza, retorna True.

    Importante:
    - Si cambias el RUT a uno ya existente (rut_normalizado UNIQUE), SQLite dará error.
    """
    # Primero verificamos si existe
    existente = obtener_cliente_por_id(cliente_id)
    if not existente:
        return False

    ok, cliente, errores = validar_y_preparar_cliente(datos)
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
        return cur.rowcount > 0

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
