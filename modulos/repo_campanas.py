# ============================================
# Archivo: modulos/repo_campanas.py
# Propósito:
#   - Crear/listar campañas (tabla campanas)
#   - Actualizar resumen (total/enviados/fallidos)
# ============================================

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .bd_sqlite import obtener_conexion
from .repo_logs import registrar_evento


def _fila_a_dict(fila) -> Dict[str, Any]:
    return dict(fila) if fila else {}


def crear_campana(nombre: str, asunto: str, cuerpo: str, criterio_json: str = "") -> int:
    """Crea campaña y retorna campana_id."""
    nombre = (nombre or "").strip()
    asunto = (asunto or "").strip()
    cuerpo = (cuerpo or "").strip()

    if not asunto:
        raise ValueError("El asunto de la campaña es obligatorio.")
    if not cuerpo:
        raise ValueError("El cuerpo de la campaña es obligatorio.")

    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO campanas (nombre, asunto, cuerpo, criterio_json)
            VALUES (?, ?, ?, ?)
            """,
            (nombre if nombre else None, asunto, cuerpo, criterio_json if criterio_json else None),
        )
        conn.commit()
        cid = int(cur.lastrowid)
        registrar_evento("campanas", "CREAR", f"campana_id={cid}")
        return cid
    finally:
        conn.close()


def listar_campanas() -> List[Dict[str, Any]]:
    """Lista campañas de más nueva a más antigua."""
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM campanas ORDER BY creada_en DESC")
        return [_fila_a_dict(f) for f in cur.fetchall()]
    finally:
        conn.close()


def obtener_campana_por_id(campana_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene una campaña por ID."""
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM campanas WHERE campana_id=?", (campana_id,))
        fila = cur.fetchone()
        return _fila_a_dict(fila) if fila else None
    finally:
        conn.close()


def actualizar_resumen_campana(campana_id: int, total: int, enviados: int, fallidos: int) -> None:
    """Actualiza contadores de la campaña."""
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE campanas
            SET total_destinatarios=?, enviados=?, fallidos=?
            WHERE campana_id=?
            """,
            (int(total), int(enviados), int(fallidos), int(campana_id)),
        )
        conn.commit()
    finally:
        conn.close()
