# ============================================
# Archivo: modulos/validaciones.py
# Propósito:
#   - Normalizar y validar datos de clientes
#   - Validar RUT chileno (dígito verificador)
#   - Preparar "nombre_busqueda" para el buscador por nombre
# ============================================

from __future__ import annotations  # Permite usar tipos como "dict | None" en Python 3.9+
import re  # Librería para expresiones regulares (validaciones simples)


# -----------------------------
# Validación básica de email
# (No es perfecta, pero sirve para un proyecto educativo)
# -----------------------------
_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")  # Patrón simple de email


def normalizar_texto(valor) -> str:
    """
    Convierte cualquier valor a texto limpio.
    - Si valor es None, devuelve "".
    - Si es algo, lo convierte a str y quita espacios.
    """
    if valor is None:
        return ""
    return str(valor).strip()


# =========================================================
# RUT: normalización y validación
# =========================================================

def rut_a_normalizado(rut: str) -> str:
    """
    Convierte un RUT a formato normalizado (para comparar y guardar en DB).
    Ejemplos:
      "12.345.678-k" -> "12345678K"
      "12345678-K"   -> "12345678K"

    Retorna:
      - String sin puntos, sin guion, DV en mayúscula.
      - Si viene vacío, retorna "".
    """
    rut = normalizar_texto(rut)  # Limpia espacios
    if not rut:
        return ""

    # Quitamos puntos y guiones
    rut = rut.replace(".", "").replace("-", "")

    # Pasamos a mayúscula
    rut = rut.upper()

    return rut


def formatear_rut(rut_normalizado: str) -> str:
    """
    Toma un RUT normalizado "12345678K" y lo devuelve en formato más legible:
      "12.345.678-K"

    Si no se puede formatear, devuelve el texto original.
    """
    rut_normalizado = normalizar_texto(rut_normalizado).upper()
    if len(rut_normalizado) < 2:
        return rut_normalizado

    cuerpo = rut_normalizado[:-1]  # Todo menos el DV
    dv = rut_normalizado[-1]       # Último caracter

    if not cuerpo.isdigit():
        return rut_normalizado

    # Agrega puntos cada 3 desde el final (formato chileno típico)
    partes = []
    while len(cuerpo) > 3:
        partes.insert(0, cuerpo[-3:])
        cuerpo = cuerpo[:-3]
    partes.insert(0, cuerpo)

    return ".".join(partes) + "-" + dv


def calcular_dv_rut(cuerpo: str) -> str:
    """
    Calcula el dígito verificador (DV) para un cuerpo de RUT (solo números).
    Regla (módulo 11):
      - multiplicadores: 2,3,4,5,6,7,2,3,...
      - se suma producto, se calcula 11 - (suma % 11)
      - resultado:
          11 -> '0'
          10 -> 'K'
          otro -> str(resultado)
    """
    # Aseguramos que cuerpo solo tenga dígitos
    if not cuerpo.isdigit():
        return ""

    # Multiplicadores según norma
    multiplicadores = [2, 3, 4, 5, 6, 7]

    suma = 0
    m = 0

    # Recorremos de derecha a izquierda
    for digit_char in reversed(cuerpo):
        dig = int(digit_char)
        suma += dig * multiplicadores[m]
        m = (m + 1) % len(multiplicadores)

    resto = suma % 11
    dv_num = 11 - resto

    if dv_num == 11:
        return "0"
    if dv_num == 10:
        return "K"
    return str(dv_num)


def rut_es_valido(rut: str) -> bool:
    """
    Verifica si un RUT es válido (estructura + DV).
    Acepta rut con puntos y guion, o sin ellos.

    Retorna True si:
      - tiene al menos 2 caracteres (cuerpo + DV)
      - cuerpo es numérico
      - DV coincide con el calculado
    """
    rut_norm = rut_a_normalizado(rut)
    if len(rut_norm) < 2:
        return False

    cuerpo = rut_norm[:-1]
    dv = rut_norm[-1]

    if not cuerpo.isdigit():
        return False

    dv_calc = calcular_dv_rut(cuerpo)
    return dv == dv_calc


# =========================================================
# Validación/normalización de email y teléfono
# =========================================================

def email_es_valido(email: str) -> bool:
    """
    Valida un email con regla simple:
      algo@algo.algo
    """
    email = normalizar_texto(email)
    if not email:
        return False
    return _RE_EMAIL.match(email) is not None


def normalizar_email(email: str) -> str:
    """
    Normaliza email:
    - quita espacios
    - convierte a minúsculas
    """
    return normalizar_texto(email).lower()


def normalizar_telefono(telefono: str) -> str:
    """
    Deja el teléfono con solo dígitos (y opcional + al inicio si lo tenía).
    Ej:
      "+56 9 1234 5678" -> "+56912345678"
      "9 1234 5678"     -> "912345678"
    """
    tel = normalizar_texto(telefono)

    # Si tenía + al inicio, lo mantenemos
    tiene_mas = tel.startswith("+")

    # Quitamos todo lo que no sea dígito
    solo_digitos = "".join(ch for ch in tel if ch.isdigit())

    if tiene_mas and solo_digitos:
        return "+" + solo_digitos

    return solo_digitos


def telefono_es_valido(telefono: str) -> bool:
    """
    Valida teléfono de forma simple:
    - Debe tener al menos 8 dígitos (ajustable)
    """
    tel = normalizar_telefono(telefono)
    # Quitamos '+' si existe para contar dígitos
    tel_sin = tel[1:] if tel.startswith("+") else tel
    return tel_sin.isdigit() and len(tel_sin) >= 8


# =========================================================
# Estado y tipo cliente
# =========================================================

def parse_estado(valor) -> int:
    """
    Convierte distintos formatos a estado 0/1:
      - "Activo" -> 1
      - "Inactivo" -> 0
      - "1"/1/True -> 1
      - "0"/0/False -> 0

    Si no se reconoce, devuelve 1 por defecto.
    """
    if isinstance(valor, bool):
        return 1 if valor else 0

    txt = normalizar_texto(valor).lower()

    if txt in ("1", "activo", "activa", "si", "sí", "true", "t", "yes", "y"):
        return 1

    if txt in ("0", "inactivo", "inactiva", "no", "false", "f", "n"):
        return 0

    return 1  # Por defecto


def parse_recibe_correos(valor) -> int:
    """
    Convierte distintos formatos a 0/1 para "recibe_correos".
    """
    return parse_estado(valor)


def construir_nombre_busqueda(tipo_cliente: str, nombres: str, apellidos: str, razon_social: str) -> str:
    """
    Construye un texto en minúsculas para buscar por nombre fácilmente.
    - Para Regular/Premium: "nombres apellidos"
    - Para Corporativo: "razon_social"
    """
    tipo = normalizar_texto(tipo_cliente)

    if tipo.lower() == "corporativo":
        return normalizar_texto(razon_social).casefold()

    # Regular o Premium (persona)
    return (normalizar_texto(nombres) + " " + normalizar_texto(apellidos)).strip().casefold()


# =========================================================
# Validación principal del cliente (para CRUD e importación)
# =========================================================

def validar_y_preparar_cliente(datos: dict) -> tuple[bool, dict | None, list[str]]:
    """
    Valida y prepara un diccionario de cliente para guardarlo en la DB.

    Entrada esperada (keys típicas):
      - tipo_cliente
      - rut
      - nombres, apellidos (si persona)
      - razon_social (si corporativo)
      - email
      - telefono
      - estado (0/1 o texto)
      - recibe_correos (0/1 o texto)
      - observaciones

    Retorna:
      (ok, cliente_preparado, errores)

    Donde cliente_preparado incluye:
      - rut_normalizado
      - nombre_busqueda
      - email normalizado
      - telefono normalizado
      - estado 0/1, recibe_correos 0/1
    """
    errores: list[str] = []

    # Tomamos campos y normalizamos texto básico
    tipo_cliente = normalizar_texto(datos.get("tipo_cliente"))
    rut = normalizar_texto(datos.get("rut"))
    nombres = normalizar_texto(datos.get("nombres"))
    apellidos = normalizar_texto(datos.get("apellidos"))
    razon_social = normalizar_texto(datos.get("razon_social"))
    email = normalizar_texto(datos.get("email"))
    telefono = normalizar_texto(datos.get("telefono"))
    observaciones = normalizar_texto(datos.get("observaciones"))

    # 1) Tipo cliente
    if tipo_cliente not in ("Regular", "Premium", "Corporativo"):
        errores.append("Tipo de cliente inválido (debe ser Regular, Premium o Corporativo).")

    # 2) RUT
    if not rut:
        errores.append("RUT es obligatorio.")
    elif not rut_es_valido(rut):
        errores.append("RUT inválido (dígito verificador no coincide).")

    rut_normalizado = rut_a_normalizado(rut)

    # 3) Reglas por tipo
    if tipo_cliente in ("Regular", "Premium"):
        if not nombres:
            errores.append("Nombres es obligatorio para clientes Regular/Premium.")
        if not apellidos:
            errores.append("Apellidos es obligatorio para clientes Regular/Premium.")
    if tipo_cliente == "Corporativo":
        if not razon_social:
            errores.append("Razón social es obligatoria para clientes Corporativo.")

    # 4) Email (si viene vacío, lo dejamos vacío; si viene, validamos)
    email_norm = ""
    if email:
        email_norm = normalizar_email(email)
        if not email_es_valido(email_norm):
            errores.append("Email inválido (formato incorrecto).")

    # 5) Teléfono (si viene vacío, lo dejamos vacío; si viene, validamos)
    tel_norm = ""
    if telefono:
        tel_norm = normalizar_telefono(telefono)
        if not telefono_es_valido(tel_norm):
            errores.append("Teléfono inválido (debe tener al menos 8 dígitos).")

    # 6) Estado y recibe_correos
    estado = parse_estado(datos.get("estado"))
    recibe_correos = parse_recibe_correos(datos.get("recibe_correos", 1))

    # 7) nombre_busqueda (para el buscador por nombre)
    nombre_busqueda = construir_nombre_busqueda(tipo_cliente, nombres, apellidos, razon_social)
    if not nombre_busqueda:
        # No debería ocurrir si las reglas anteriores están bien, pero lo protegemos
        errores.append("No se pudo construir el nombre de búsqueda (faltan datos).")

    # Si hay errores, retornamos sin preparar el cliente
    if errores:
        return False, None, errores

    # Preparamos el dict final que se guardará
    cliente_preparado = {
        "tipo_cliente": tipo_cliente,
        "rut": formatear_rut(rut_normalizado),        # guardamos bonito (opcional, pero útil)
        "rut_normalizado": rut_normalizado,           # guardamos normalizado (clave única)
        "nombres": nombres if nombres else None,
        "apellidos": apellidos if apellidos else None,
        "razon_social": razon_social if razon_social else None,
        "email": email_norm if email_norm else None,
        "telefono": tel_norm if tel_norm else None,
        "estado": estado,
        "recibe_correos": recibe_correos,
        "nombre_busqueda": nombre_busqueda,
        "observaciones": observaciones if observaciones else None,
    }

    return True, cliente_preparado, []
