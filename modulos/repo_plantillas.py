# ============================================
# Archivo: modulos/repo_plantillas.py
# Propósito:
#   - CRUD de plantillas de correo en SQLite (tabla plantillas_correo)
# ============================================

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .bd_sqlite import obtener_conexion
from .repo_logs import registrar_evento


def _fila_a_dict(fila) -> Dict[str, Any]:
    """Convierte sqlite3.Row a dict normal."""
    return dict(fila) if fila else {}


def listar_plantillas(incluir_inactivas: bool = True) -> List[Dict[str, Any]]:
    """Lista plantillas (todas o solo activas)."""
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        if incluir_inactivas:
            cur.execute("SELECT * FROM plantillas_correo ORDER BY nombre ASC")
        else:
            cur.execute("SELECT * FROM plantillas_correo WHERE activa=1 ORDER BY nombre ASC")
        return [_fila_a_dict(f) for f in cur.fetchall()]
    finally:
        conn.close()


def obtener_plantilla_por_id(plantilla_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene una plantilla por su ID."""
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM plantillas_correo WHERE plantilla_id=?", (plantilla_id,))
        fila = cur.fetchone()
        return _fila_a_dict(fila) if fila else None
    finally:
        conn.close()


def crear_plantilla(nombre: str, asunto: str, cuerpo: str, activa: int = 1) -> int:
    """Crea una plantilla y retorna plantilla_id."""
    nombre = (nombre or "").strip()
    asunto = (asunto or "").strip()
    cuerpo = (cuerpo or "").strip()
    activa = 1 if int(activa) == 1 else 0

    if not nombre:
        raise ValueError("El nombre de la plantilla es obligatorio.")
    if not asunto:
        raise ValueError("El asunto de la plantilla es obligatorio.")
    if not cuerpo:
        raise ValueError("El cuerpo de la plantilla es obligatorio.")

    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO plantillas_correo (nombre, asunto, cuerpo, activa)
            VALUES (?, ?, ?, ?)
            """,
            (nombre, asunto, cuerpo, activa),
        )
        conn.commit()
        pid = int(cur.lastrowid)
        registrar_evento("plantillas", "CREAR", f"plantilla_id={pid} nombre='{nombre}'")
        return pid
    finally:
        conn.close()


def actualizar_plantilla(plantilla_id: int, nombre: str, asunto: str, cuerpo: str, activa: int = 1) -> bool:
    """Actualiza una plantilla. Retorna True si actualizó."""
    nombre = (nombre or "").strip()
    asunto = (asunto or "").strip()
    cuerpo = (cuerpo or "").strip()
    activa = 1 if int(activa) == 1 else 0

    if not nombre:
        raise ValueError("El nombre de la plantilla es obligatorio.")
    if not asunto:
        raise ValueError("El asunto de la plantilla es obligatorio.")
    if not cuerpo:
        raise ValueError("El cuerpo de la plantilla es obligatorio.")

    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE plantillas_correo
            SET nombre=?, asunto=?, cuerpo=?, activa=?
            WHERE plantilla_id=?
            """,
            (nombre, asunto, cuerpo, activa, plantilla_id),
        )
        conn.commit()
        ok = cur.rowcount > 0
        if ok:
            registrar_evento("plantillas", "ACTUALIZAR", f"plantilla_id={plantilla_id} nombre='{nombre}'")
        return ok
    finally:
        conn.close()


def eliminar_plantilla(plantilla_id: int) -> bool:
    """Elimina una plantilla. Retorna True si eliminó."""
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM plantillas_correo WHERE plantilla_id=?", (plantilla_id,))
        conn.commit()
        ok = cur.rowcount > 0
        if ok:
            registrar_evento("plantillas", "ELIMINAR", f"plantilla_id={plantilla_id}")
        return ok
    finally:
        conn.close()
