# ============================================
# Archivo: modulos/config.py
# Propósito:
#   - Centralizar rutas y constantes del sistema
#   - Definir dónde se guardará la BD y config local (AppData)
# ============================================

import os  # Permite trabajar con rutas del sistema operativo


# Nombre "oficial" de la aplicación (se usa para crear carpetas en AppData)
NOMBRE_APP = "GIC"  # Gestor Inteligente de Clientes


def obtener_directorio_appdata() -> str:
    """
    Devuelve la carpeta AppData/Roaming del usuario actual.
    En Windows suele ser algo como:
    C:\\Users\\<usuario>\\AppData\\Roaming
    """
    # APPDATA es una variable de entorno típica en Windows
    appdata = os.getenv("APPDATA")  # Puede devolver None si algo raro ocurre
    # Si por alguna razón APPDATA no existe, usamos el home del usuario como respaldo
    if not appdata:
        appdata = os.path.expanduser("~")  # Ej: C:\Users\Cesar
    return appdata  # Retornamos la ruta base


def obtener_directorio_datos() -> str:
    """
    Devuelve la carpeta donde se guardarán los datos del sistema (BD, config).
    Ejemplo:
      AppData\\Roaming\\GIC\\data
    """
    # Construimos la ruta final usando os.path.join para que quede correcta
    ruta = os.path.join(obtener_directorio_appdata(), NOMBRE_APP, "data")
    # Creamos la carpeta si no existe (exist_ok=True evita error si ya existe)
    os.makedirs(ruta, exist_ok=True)
    return ruta


def obtener_ruta_bd() -> str:
    """
    Devuelve la ruta completa del archivo de base de datos SQLite.
    Ejemplo:
      AppData\\Roaming\\GIC\\data\\gic.db
    """
    return os.path.join(obtener_directorio_datos(), "gic.db")


def obtener_directorio_config() -> str:
    """
    Carpeta para configuraciones (por ejemplo credenciales Gmail).
    Ejemplo:
      AppData\\Roaming\\GIC\\config
    """
    ruta = os.path.join(obtener_directorio_appdata(), NOMBRE_APP, "config")
    os.makedirs(ruta, exist_ok=True)
    return ruta


def obtener_ruta_config_correo() -> str:
    """
    Ruta donde se guardará la configuración de correo (Gmail) localmente.
    Importante: este archivo NO debe subirse a GitHub.
    """
    return os.path.join(obtener_directorio_config(), "correo.json")
