-- =========================================================
-- Base de Datos SQLite - Gestor Inteligente de Clientes (GIC)
-- Archivo: scripts/crear_bd.sql
-- Objetivo:
--   - Crear tablas para: clientes, categorías, plantillas, campañas, envíos, logs.
--   - Preparar vistas listas para exportar a Excel/PDF.
-- Nota:
--   - Se usa RUT como identificador lógico del cliente.
--   - Se usa rut_normalizado para evitar duplicados por formato.
-- =========================================================

PRAGMA foreign_keys = ON; -- Activa claves foráneas (muy importante en SQLite)

-- =========================================================
-- TABLA: clientes
-- Guarda datos principales del cliente y banderas para envíos masivos.
-- =========================================================
CREATE TABLE IF NOT EXISTS clientes (
    cliente_id          INTEGER PRIMARY KEY AUTOINCREMENT, -- ID interno (PK)

    tipo_cliente        TEXT NOT NULL
                        CHECK (tipo_cliente IN ('Regular','Premium','Corporativo')), -- Tipo requerido

    rut                 TEXT NOT NULL,         -- RUT en formato libre (ej: 12.345.678-K)
    rut_normalizado     TEXT NOT NULL UNIQUE,  -- RUT normalizado (ej: 12345678K) evita duplicados

    nombres             TEXT,                  -- Para personas (Regular/Premium)
    apellidos           TEXT,                  -- Para personas (Regular/Premium)
    razon_social        TEXT,                  -- Para empresas (Corporativo)

    email               TEXT,                  -- Correo del cliente (destinatario)
    telefono            TEXT,                  -- Teléfono del cliente

    recibe_correos      INTEGER NOT NULL DEFAULT 1 CHECK (recibe_correos IN (0,1)), -- 1=Sí, 0=No
    estado              INTEGER NOT NULL DEFAULT 1 CHECK (estado IN (0,1)),         -- 1=Activo, 0=Inactivo

    nombre_busqueda     TEXT NOT NULL, -- Texto preparado para búsqueda (en minúsculas): "juan perez" / "acme spa"

    fecha_registro      TEXT NOT NULL DEFAULT (datetime('now')), -- Fecha creación
    fecha_actualizacion TEXT NOT NULL DEFAULT (datetime('now')), -- Fecha última modificación
    observaciones       TEXT, -- Notas libres

    -- Regla: si es persona, debe tener nombres y apellidos; si es corporativo, razón social.
    CHECK (
        (tipo_cliente IN ('Regular','Premium') AND nombres IS NOT NULL AND apellidos IS NOT NULL)
        OR
        (tipo_cliente = 'Corporativo' AND razon_social IS NOT NULL)
    )
);

-- Índices para acelerar búsquedas/listados
CREATE INDEX IF NOT EXISTS idx_clientes_nombre_busqueda ON clientes(nombre_busqueda);
CREATE INDEX IF NOT EXISTS idx_clientes_estado ON clientes(estado);
CREATE INDEX IF NOT EXISTS idx_clientes_recibe_correos ON clientes(recibe_correos);

-- Trigger para actualizar fecha_actualizacion cuando se modifica un cliente
CREATE TRIGGER IF NOT EXISTS trg_clientes_actualiza_fecha
AFTER UPDATE ON clientes
FOR EACH ROW
BEGIN
    UPDATE clientes
    SET fecha_actualizacion = datetime('now')
    WHERE cliente_id = OLD.cliente_id;
END;

-- =========================================================
-- TABLA: categorias
-- Categorías libres (Newsletter, Ofertas, VIP, etc.)
-- =========================================================
CREATE TABLE IF NOT EXISTS categorias (
    categoria_id    INTEGER PRIMARY KEY AUTOINCREMENT, -- PK
    nombre          TEXT NOT NULL UNIQUE,               -- Nombre único
    descripcion     TEXT,                               -- Descripción opcional
    activa          INTEGER NOT NULL DEFAULT 1 CHECK (activa IN (0,1)), -- 1=Activa, 0=Inactiva
    creada_en       TEXT NOT NULL DEFAULT (datetime('now'))             -- Fecha creación
);

-- =========================================================
-- TABLA: cliente_categorias (relación N a N)
-- Un cliente puede pertenecer a muchas categorías.
-- =========================================================
CREATE TABLE IF NOT EXISTS cliente_categorias (
    cliente_id      INTEGER NOT NULL, -- FK a clientes
    categoria_id    INTEGER NOT NULL, -- FK a categorias
    asignada_en     TEXT NOT NULL DEFAULT (datetime('now')), -- Fecha asignación

    PRIMARY KEY (cliente_id, categoria_id), -- Evita duplicados (misma categoría repetida)
    FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id) ON DELETE CASCADE,
    FOREIGN KEY (categoria_id) REFERENCES categorias(categoria_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cc_categoria ON cliente_categorias(categoria_id);

-- =========================================================
-- TABLA: plantillas_correo
-- Plantillas reutilizables para cartas/correos masivos.
-- Variables sugeridas: {nombre}, {apellidos}, {razon_social}, {rut}
-- =========================================================
CREATE TABLE IF NOT EXISTS plantillas_correo (
    plantilla_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL UNIQUE, -- Nombre interno de la plantilla
    asunto          TEXT NOT NULL,        -- Asunto del correo
    cuerpo          TEXT NOT NULL,        -- Texto del correo
    activa          INTEGER NOT NULL DEFAULT 1 CHECK (activa IN (0,1)),
    creada_en       TEXT NOT NULL DEFAULT (datetime('now'))
);

-- =========================================================
-- TABLA: campanas
-- Cada campaña representa un envío masivo (asunto + cuerpo + criterio)
-- criterio_json permite guardar filtros (categorías/IDs seleccionados).
-- =========================================================
CREATE TABLE IF NOT EXISTS campanas (
    campana_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre              TEXT,                      -- Nombre opcional
    asunto              TEXT NOT NULL,             -- Asunto usado en la campaña
    cuerpo              TEXT NOT NULL,             -- Cuerpo usado en la campaña
    criterio_json       TEXT,                      -- JSON con selección (opcional)
    total_destinatarios INTEGER NOT NULL DEFAULT 0, -- Total planificado
    enviados            INTEGER NOT NULL DEFAULT 0, -- Total enviados OK
    fallidos            INTEGER NOT NULL DEFAULT 0, -- Total con error
    creada_en           TEXT NOT NULL DEFAULT (datetime('now'))
);

-- =========================================================
-- TABLA: envios_detalle
-- Un registro por destinatario de una campaña.
-- Estados:
--   - PENDIENTE: creado pero aún no enviado
--   - ENVIADO: enviado correctamente
--   - ERROR: falló (guardar el mensaje)
--   - OMITIDO: no se envió (sin email, no recibe correos, inactivo, etc.)
-- =========================================================
CREATE TABLE IF NOT EXISTS envios_detalle (
    envio_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    campana_id       INTEGER NOT NULL, -- FK a campanas
    cliente_id       INTEGER,          -- FK a clientes (puede ser NULL si se usa correo externo)
    email_destino    TEXT NOT NULL,    -- Email al que se intentó enviar
    estado           TEXT NOT NULL
                    CHECK (estado IN ('PENDIENTE','ENVIADO','ERROR','OMITIDO'))
                    DEFAULT 'PENDIENTE',
    error_mensaje    TEXT,             -- Si falló, guardar el error
    enviado_en       TEXT,             -- Fecha/hora del envío (si aplica)

    FOREIGN KEY (campana_id) REFERENCES campanas(campana_id) ON DELETE CASCADE,
    FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_envios_campana ON envios_detalle(campana_id);
CREATE INDEX IF NOT EXISTS idx_envios_estado ON envios_detalle(estado);

-- =========================================================
-- TABLA: logs_eventos
-- Bitácora general: CRUD, importación Excel, exportaciones, correos, errores.
-- =========================================================
CREATE TABLE IF NOT EXISTS logs_eventos (
    log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora   TEXT NOT NULL DEFAULT (datetime('now')),
    modulo       TEXT NOT NULL, -- ej: "clientes", "importacion", "correo"
    accion       TEXT NOT NULL, -- ej: "CREAR", "ACTUALIZAR", "ELIMINAR", "ENVIAR"
    detalle      TEXT,          -- texto legible
    nivel        TEXT NOT NULL DEFAULT 'INFO'
                 CHECK (nivel IN ('INFO','WARN','ERROR'))
);

CREATE INDEX IF NOT EXISTS idx_logs_fecha ON logs_eventos(fecha_hora);
CREATE INDEX IF NOT EXISTS idx_logs_modulo ON logs_eventos(modulo);

-- =========================================================
-- VISTA: vw_clientes_exportacion
-- Lista plana lista para exportar a Excel/PDF (sin joins complejos).
-- =========================================================
CREATE VIEW IF NOT EXISTS vw_clientes_exportacion AS
SELECT
    cliente_id,
    tipo_cliente,
    rut,
    rut_normalizado,
    COALESCE(razon_social, (nombres || ' ' || apellidos)) AS nombre_mostrado,
    email,
    telefono,
    estado,
    recibe_correos,
    fecha_registro,
    fecha_actualizacion,
    observaciones
FROM clientes;

-- =========================================================
-- VISTA: vw_campanas_resumen_exportacion
-- Resumen de campañas listo para reportes.
-- =========================================================
CREATE VIEW IF NOT EXISTS vw_campanas_resumen_exportacion AS
SELECT
    campana_id,
    nombre,
    asunto,
    total_destinatarios,
    enviados,
    fallidos,
    creada_en
FROM campanas;
