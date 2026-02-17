# ============================================
# Archivo: modulos/repo_logs.py
# Propósito:
#   - Registrar eventos en la tabla logs_eventos (SQLite)
#   - Usarlo para CRUD, importación, exportación y correos
# ============================================

from __future__ import annotations
from .bd_sqlite import obtener_conexion


def registrar_evento(modulo: str, accion: str, detalle: str = "", nivel: str = "INFO") -> None:
    """
    Inserta un evento en logs_eventos.

    Parámetros:
      - modulo: nombre del módulo (ej: "clientes", "importacion", "exportacion", "correo")
      - accion: acción realizada (ej: "CREAR", "ACTUALIZAR", "ELIMINAR", "IMPORTAR")
      - detalle: texto explicativo para auditoría
      - nivel: INFO / WARN / ERROR
    """
    conn = obtener_conexion()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO logs_eventos (modulo, accion, detalle, nivel)
            VALUES (?, ?, ?, ?)
            """,
            (modulo, accion, detalle, nivel),
        )
        conn.commit()
    finally:
        conn.close()
