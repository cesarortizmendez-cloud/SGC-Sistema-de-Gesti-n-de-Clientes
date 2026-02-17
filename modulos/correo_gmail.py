# ============================================
# Archivo: modulos/correo_gmail.py
# Propósito:
#   - Guardar / cargar configuración de Gmail (local en AppData)
#   - Enviar correos usando SMTP de Gmail (con contraseña de aplicación)
#   - Probar envío para verificar configuración
# ============================================

from __future__ import annotations

import json  # Para guardar/leer configuración en JSON
import os  # Para verificar existencia de archivos
import smtplib  # Cliente SMTP (enviar correos)
from email.mime.text import MIMEText  # Cuerpo del correo (texto)
from email.mime.multipart import MIMEMultipart  # Mensaje completo (asunto + cuerpo)

from .config import obtener_ruta_config_correo  # Ruta local AppData para guardar correo.json


SMTP_SERVER = "smtp.gmail.com"  # Servidor SMTP de Gmail
SMTP_PORT = 587  # Puerto TLS recomendado


def cargar_config_correo() -> dict:
    """
    Carga la configuración del correo desde AppData.
    Si no existe archivo, devuelve un dict vacío.
    """
    ruta = obtener_ruta_config_correo()  # Ruta donde guardamos la config
    if not os.path.exists(ruta):  # Si no existe, no hay config aún
        return {}
    with open(ruta, "r", encoding="utf-8") as f:  # Abrimos el archivo
        return json.load(f)  # Leemos JSON y lo devolvemos


def guardar_config_correo(config: dict) -> None:
    """
    Guarda la configuración del correo en AppData (correo.json).
    """
    ruta = obtener_ruta_config_correo()  # Ruta de guardado
    with open(ruta, "w", encoding="utf-8") as f:  # Abrimos en modo escritura
        json.dump(config, f, indent=2, ensure_ascii=False)  # Guardamos JSON bonito


def config_es_valida(config: dict) -> tuple[bool, str]:
    """
    Valida que existan los campos mínimos para enviar correo.
    Retorna (ok, mensaje).
    """
    correo = (config.get("correo") or "").strip()
    app_password = (config.get("app_password") or "").strip()

    if not correo:
        return False, "Falta el correo Gmail (remitente)."
    if not app_password:
        return False, "Falta la contraseña de aplicación (App Password)."

    return True, "OK"


def enviar_correo(
    destinatario: str,
    asunto: str,
    cuerpo: str,
    config: dict | None = None,
) -> None:
    """
    Envía un correo (texto plano) usando Gmail SMTP.

    - destinatario: email destino
    - asunto: asunto del correo
    - cuerpo: contenido del correo (texto)
    - config: si es None, se carga desde AppData automáticamente

    Lanza excepción si falla (para que la UI lo registre como ERROR).
    """
    if config is None:
        config = cargar_config_correo()  # Si no entregan config, la cargamos

    ok, msg = config_es_valida(config)  # Validamos config
    if not ok:
        raise ValueError(msg)

    remitente = config.get("correo")  # Gmail remitente
    app_password = config.get("app_password")  # Contraseña de aplicación
    nombre_remitente = (config.get("nombre_remitente") or "").strip()  # opcional

    # Construimos el mensaje MIME
    mensaje = MIMEMultipart()  # Mensaje completo
    mensaje["From"] = f"{nombre_remitente} <{remitente}>" if nombre_remitente else remitente
    mensaje["To"] = destinatario
    mensaje["Subject"] = asunto

    # Adjuntamos cuerpo como texto plano
    mensaje.attach(MIMEText(cuerpo, "plain", "utf-8"))

    # Conectamos a Gmail y enviamos
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as servidor:
        servidor.ehlo()  # Saludo inicial
        servidor.starttls()  # Inicia cifrado TLS
        servidor.ehlo()  # Segundo saludo ya en TLS
        servidor.login(remitente, app_password)  # Login con app password
        servidor.sendmail(remitente, destinatario, mensaje.as_string())  # Envío real


def probar_envio(destinatario_prueba: str) -> None:
    """
    Envía un correo de prueba al email indicado.
    Usa la configuración guardada en AppData.
    """
    asunto = "Prueba SGC - Configuración Gmail"
    cuerpo = "Este es un correo de prueba enviado desde SGC (Tkinter + SQLite)."
    enviar_correo(destinatario_prueba, asunto, cuerpo, config=None)
