# ============================================
# Archivo: modulos/repo_categorias.py
# Propósito:
#   - CRUD de categorías (tabla categorias)
#   - Asignación de categorías a clientes (tabla cliente_categorias)
#   - Funciones pensadas para UI y mensajería masiva
# ============================================

from __future__ import annotations  # Tipos modernos
from typing import Any, Dict, List, Optional  # Tipos para claridad

from .bd_sqlite import obtener_conexion  # Conexión SQLite
from .repo_logs import registrar_evento  # Logs en BD


def _fila_a_dict(fila) -> Dict[str, Any]:
    """Convierte sqlite3.Row a dict normal."""
    return dict(fila) if fila is not None else {}


# =========================================================
# CRUD de categorías
# =========================================================

def listar_categorias(incluir_inactivas: bool = True) -> List[Dict[str, Any]]:
    """
    Lista categorías.
    - incluir_inactivas=True: trae todas
    - incluir_inactivas=False: trae solo activas
    """
    conn = obtener_conexion()
    try:
        cur = conn.cursor()

        if incluir_inactivas:
            cur.execute("SELECT * FROM categorias ORDER BY nombre ASC")
        else:
            cur.execute("SELECT * FROM categorias WHERE activa = 1 ORDER BY nombre ASC")

        filas = cur.fetchall()
        return [_fila_a_dict(f) for f in filas]
    finally:
        conn.close()


def obtener_categoria_por_id(categoria_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene una categoría por su ID."""
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM categorias WHERE categoria_id = ?", (categoria_id,))
        fila = cur.fetchone()
        return _fila_a_dict(fila) if fila else None
    finally:
        conn.close()


def crear_categoria(nombre: str, descripcion: str = "", activa: int = 1) -> int:
    """
    Crea una categoría.
    - nombre es UNIQUE en BD, por lo tanto si se repite, SQLite lanzará error.
    Retorna categoria_id.
    """
    nombre = (nombre or "").strip()
    descripcion = (descripcion or "").strip()
    activa = 1 if int(activa) == 1 else 0

    if not nombre:
        raise ValueError("El nombre de la categoría es obligatorio.")

    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO categorias (nombre, descripcion, activa)
            VALUES (?, ?, ?)
            """,
            (nombre, descripcion if descripcion else None, activa),
        )
        conn.commit()

        cat_id = int(cur.lastrowid)
        registrar_evento("categorias", "CREAR", f"categoria_id={cat_id} nombre='{nombre}'")
        return cat_id
    finally:
        conn.close()


def actualizar_categoria(categoria_id: int, nombre: str, descripcion: str = "", activa: int = 1) -> bool:
    """
    Actualiza una categoría existente.
    Retorna True si actualizó, False si no existía.
    """
    nombre = (nombre or "").strip()
    descripcion = (descripcion or "").strip()
    activa = 1 if int(activa) == 1 else 0

    if not nombre:
        raise ValueError("El nombre de la categoría es obligatorio.")

    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE categorias
            SET nombre = ?, descripcion = ?, activa = ?
            WHERE categoria_id = ?
            """,
            (nombre, descripcion if descripcion else None, activa, categoria_id),
        )
        conn.commit()

        ok = cur.rowcount > 0
        if ok:
            registrar_evento("categorias", "ACTUALIZAR", f"categoria_id={categoria_id} nombre='{nombre}'")
        return ok
    finally:
        conn.close()


def eliminar_categoria(categoria_id: int) -> bool:
    """
    Elimina una categoría.
    - Por FK ON DELETE CASCADE, se eliminan asignaciones en cliente_categorias.
    """
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM categorias WHERE categoria_id = ?", (categoria_id,))
        conn.commit()

        ok = cur.rowcount > 0
        if ok:
            registrar_evento("categorias", "ELIMINAR", f"categoria_id={categoria_id}")
        return ok
    finally:
        conn.close()


# =========================================================
# Asignación categorías ↔ clientes
# =========================================================

def obtener_ids_categorias_de_cliente(cliente_id: int) -> List[int]:
    """
    Devuelve lista de categoria_id asignadas a un cliente.
    """
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT categoria_id
            FROM cliente_categorias
            WHERE cliente_id = ?
            """,
            (cliente_id,),
        )
        filas = cur.fetchall()
        return [int(f["categoria_id"]) for f in filas]
    finally:
        conn.close()


def listar_categorias_de_cliente(cliente_id: int) -> List[Dict[str, Any]]:
    """
    Devuelve las categorías (completas) asignadas a un cliente.
    """
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.*
            FROM categorias c
            INNER JOIN cliente_categorias cc ON cc.categoria_id = c.categoria_id
            WHERE cc.cliente_id = ?
            ORDER BY c.nombre ASC
            """,
            (cliente_id,),
        )
        filas = cur.fetchall()
        return [_fila_a_dict(f) for f in filas]
    finally:
        conn.close()


def set_categorias_cliente(cliente_id: int, categoria_ids: List[int]) -> None:
    """
    Define EXACTAMENTE las categorías de un cliente.
    - Borra asignaciones anteriores
    - Inserta las nuevas (sin duplicados)
    """
    # Quitamos duplicados manteniendo solo IDs válidos enteros
    ids_limpios = []
    vistos = set()
    for cid in categoria_ids:
        try:
            cid_int = int(cid)
        except Exception:
            continue
        if cid_int not in vistos:
            vistos.add(cid_int)
            ids_limpios.append(cid_int)

    conn = obtener_conexion()
    try:
        cur = conn.cursor()

        # 1) Borrar todas las categorías anteriores del cliente
        cur.execute("DELETE FROM cliente_categorias WHERE cliente_id = ?", (cliente_id,))

        # 2) Insertar las nuevas
        for categoria_id in ids_limpios:
            cur.execute(
                """
                INSERT INTO cliente_categorias (cliente_id, categoria_id)
                VALUES (?, ?)
                """,
                (cliente_id, categoria_id),
            )

        conn.commit()

        registrar_evento(
            "categorias",
            "ASIGNAR",
            f"cliente_id={cliente_id} categorias={ids_limpios}",
        )

    finally:
        conn.close()
