# ============================================
# Archivo: modulos/repo_envios.py
# Propósito:
#   - Manejar envíos (tabla envios_detalle)
#   - Crear detalle de destinatarios para una campaña
#   - Actualizar estado: ENVIADO / ERROR / OMITIDO
# ============================================

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .bd_sqlite import obtener_conexion


def _fila_a_dict(fila) -> Dict[str, Any]:
    return dict(fila) if fila else {}


def crear_detalle_envios(campana_id: int, clientes: List[Dict[str, Any]]) -> Tuple[int, int, int]:
    """
    Crea registros en envios_detalle para una campaña.

    Regla:
      - Si cliente está activo + recibe_correos + tiene email -> PENDIENTE
      - Si no -> OMITIDO con razón en error_mensaje

    Retorna: (total, pendientes, omitidos)
    """
    total = 0
    pendientes = 0
    omitidos = 0

    conn = obtener_conexion()
    try:
        cur = conn.cursor()

        for c in clientes:
            total += 1

            cliente_id = c.get("cliente_id")
            email = (c.get("email") or "").strip()
            estado = int(c.get("estado", 1))
            recibe = int(c.get("recibe_correos", 1))

            # Determinamos estado inicial y motivo
            if estado != 1:
                estado_envio = "OMITIDO"
                motivo = "Cliente inactivo."
                omitidos += 1
            elif recibe != 1:
                estado_envio = "OMITIDO"
                motivo = "Cliente no acepta correos."
                omitidos += 1
            elif not email:
                estado_envio = "OMITIDO"
                motivo = "Cliente sin email."
                omitidos += 1
            else:
                estado_envio = "PENDIENTE"
                motivo = None
                pendientes += 1

            cur.execute(
                """
                INSERT INTO envios_detalle (campana_id, cliente_id, email_destino, estado, error_mensaje)
                VALUES (?, ?, ?, ?, ?)
                """,
                (campana_id, cliente_id, email if email else "SIN_EMAIL", estado_envio, motivo),
            )

        conn.commit()
        return total, pendientes, omitidos

    finally:
        conn.close()


def listar_envios_por_campana(campana_id: int) -> List[Dict[str, Any]]:
    """Lista envíos por campaña (todos)."""
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM envios_detalle
            WHERE campana_id=?
            ORDER BY envio_id ASC
            """,
            (campana_id,),
        )
        return [_fila_a_dict(f) for f in cur.fetchall()]
    finally:
        conn.close()


def listar_envios_pendientes(campana_id: int) -> List[Dict[str, Any]]:
    """Lista SOLO los envíos PENDIENTE."""
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT *
            FROM envios_detalle
            WHERE campana_id=? AND estado='PENDIENTE'
            ORDER BY envio_id ASC
            """,
            (campana_id,),
        )
        return [_fila_a_dict(f) for f in cur.fetchall()]
    finally:
        conn.close()


def marcar_envio_enviado(envio_id: int) -> None:
    """Marca un envío como ENVIADO y registra fecha/hora."""
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE envios_detalle
            SET estado='ENVIADO', enviado_en=datetime('now'), error_mensaje=NULL
            WHERE envio_id=?
            """,
            (envio_id,),
        )
        conn.commit()
    finally:
        conn.close()


def marcar_envio_error(envio_id: int, mensaje_error: str) -> None:
    """Marca un envío como ERROR, guarda mensaje."""
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE envios_detalle
            SET estado='ERROR', error_mensaje=?, enviado_en=datetime('now')
            WHERE envio_id=?
            """,
            (mensaje_error[:500], envio_id),
        )
        conn.commit()
    finally:
        conn.close()


def contar_estados(campana_id: int) -> Tuple[int, int, int]:
    """
    Cuenta estados de una campaña:
      - total
      - enviados
      - fallidos (ERROR)
    """
    conn = obtener_conexion()
    try:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) AS n FROM envios_detalle WHERE campana_id=?", (campana_id,))
        total = int(cur.fetchone()["n"])

        cur.execute("SELECT COUNT(*) AS n FROM envios_detalle WHERE campana_id=? AND estado='ENVIADO'", (campana_id,))
        enviados = int(cur.fetchone()["n"])

        cur.execute("SELECT COUNT(*) AS n FROM envios_detalle WHERE campana_id=? AND estado='ERROR'", (campana_id,))
        fallidos = int(cur.fetchone()["n"])

        return total, enviados, fallidos

    finally:
        conn.close()
