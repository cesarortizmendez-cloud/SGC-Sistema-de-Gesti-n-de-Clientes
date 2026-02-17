# ============================================
# Archivo: modulos/bd_sqlite.py
# Propósito:
#   - Crear y abrir conexión a SQLite
#   - Inicializar la BD ejecutando scripts/crear_bd.sql
#   - Funciona en modo desarrollo y en .exe (PyInstaller)
# ============================================

import os  # Para rutas y verificar existencia de archivos
import sys  # Para detectar modo PyInstaller (sys._MEIPASS)
import sqlite3  # Motor SQLite incluido en Python
from typing import Optional  # Para indicar valores opcionales

from .config import obtener_ruta_bd  # Traemos la ruta de la BD desde config


def ruta_recurso(relativa: str) -> str:
    """
    Devuelve la ruta real de un archivo del proyecto.

    - En desarrollo: se resuelve desde la carpeta raíz del proyecto.
    - En PyInstaller onefile: se resuelve desde sys._MEIPASS (carpeta temporal interna).

    Ejemplo:
      ruta_recurso("scripts/crear_bd.sql")
    """
    # Si existe sys._MEIPASS, significa que estamos en un ejecutable de PyInstaller
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS  # Carpeta temporal donde PyInstaller extrae recursos
    else:
        # En desarrollo, la base será la carpeta raíz del proyecto:
        # modulos/ está dentro del root, por eso subimos 1 nivel.
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    # Unimos base + ruta relativa para obtener la ruta completa
    return os.path.join(base, relativa)


def obtener_conexion(ruta_bd: Optional[str] = None) -> sqlite3.Connection:
    """
    Abre una conexión a SQLite y retorna el objeto Connection.

    - Si ruta_bd es None, usa la ruta por defecto en AppData (config.py).
    - Configura row_factory para obtener filas como diccionarios "tipo Row".
    - Activa foreign_keys (claves foráneas) para que ON DELETE CASCADE funcione.
    """
    # Si no se entrega ruta, usamos la ruta oficial del sistema
    if ruta_bd is None:
        ruta_bd = obtener_ruta_bd()

    # Abrimos la conexión a SQLite (crea el archivo si no existe)
    conn = sqlite3.connect(ruta_bd)

    # row_factory hace que cada fila se parezca a un dict (sqlite3.Row)
    conn.row_factory = sqlite3.Row

    # Activamos claves foráneas (importante en SQLite)
    conn.execute("PRAGMA foreign_keys = ON;")

    # Retornamos la conexión lista para usar
    return conn


def ejecutar_script_sql(conn: sqlite3.Connection, ruta_sql: str) -> None:
    """
    Lee un archivo .sql y ejecuta su contenido completo con executescript().

    - Esto permite crear tablas, índices, triggers y vistas.
    - Nuestro SQL usa IF NOT EXISTS, por eso es seguro ejecutarlo varias veces.
    """
    # Abrimos el archivo SQL en modo lectura con UTF-8 (soporta tildes)
    with open(ruta_sql, "r", encoding="utf-8") as f:
        script = f.read()  # Leemos todo el contenido del archivo

    # Ejecutamos el script SQL completo
    conn.executescript(script)

    # Guardamos cambios en la BD
    conn.commit()


def inicializar_bd() -> str:
    """
    Inicializa la base de datos si es necesario.

    Proceso:
      1) Obtiene la ruta de la BD en AppData.
      2) Abre conexión.
      3) Ejecuta scripts/crear_bd.sql.
      4) Cierra conexión.
      5) Devuelve la ruta de la BD.

    Retorna:
      - ruta del archivo .db (para mostrarla o registrar logs).
    """
    # Ruta donde quedará el archivo gic.db
    ruta_bd = obtener_ruta_bd()

    # Ruta del archivo SQL de creación
    ruta_sql = ruta_recurso(os.path.join("scripts", "crear_bd.sql"))

    # Abrimos conexión (crea el archivo si no existe)
    conn = obtener_conexion(ruta_bd)

    try:
        # Ejecutamos el SQL para crear tablas/vistas/índices si no existen
        ejecutar_script_sql(conn, ruta_sql)
    finally:
        # Siempre cerramos conexión (aunque ocurra un error)
        conn.close()

    # Retornamos la ruta para uso posterior (logs o debug)
    return ruta_bd


# Si ejecutas este archivo directamente, hará una prueba rápida creando la BD.
if __name__ == "__main__":
    # Inicializamos la BD y mostramos dónde quedó guardada
    ruta = inicializar_bd()
    print("BD inicializada en:", ruta)
