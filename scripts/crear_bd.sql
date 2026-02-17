-- =========================================================
-- Base de Datos SQLite - Sistema de Gestión de Clientes (SGC/GIC)
-- Archivo: scripts/crear_bd.sql
-- Objetivo:
--   - Crear tablas para: clientes, plantillas, campañas, envíos, logs.
--   - Usar "tipo_cliente" como la "categoría" principal:
--       Regular / Premium / Corporativo
-- =========================================================

PRAGMA foreign_keys = ON;

-- =========================================================
-- TABLA: clientes
-- =========================================================
CREATE TABLE IF NOT EXISTS clientes (
    cliente_id          INTEGER PRIMARY KEY AUTOINCREMENT,

    tipo_cliente        TEXT NOT NULL
                        CHECK (tipo_cliente IN ('Regular','Premium','Corporativo')),

    rut                 TEXT NOT NULL,
    rut_normalizado     TEXT NOT NULL UNIQUE,

    nombres             TEXT,
    apellidos           TEXT,
    razon_social        TEXT,

    email               TEXT,
    telefono            TEXT,

    recibe_correos      INTEGER NOT NULL DEFAULT 1 CHECK (recibe_correos IN (0,1)),
    estado              INTEGER NOT NULL DEFAULT 1 CHECK (estado IN (0,1)),

    nombre_busqueda     TEXT NOT NULL,

    fecha_registro      TEXT NOT NULL DEFAULT (datetime('now')),
    fecha_actualizacion TEXT NOT NULL DEFAULT (datetime('now')),
    observaciones       TEXT,

    CHECK (
        (tipo_cliente IN ('Regular','Premium') AND nombres IS NOT NULL AND apellidos IS NOT NULL)
        OR
        (tipo_cliente = 'Corporativo' AND razon_social IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_clientes_nombre_busqueda ON clientes(nombre_busqueda);
CREATE INDEX IF NOT EXISTS idx_clientes_estado ON clientes(estado);
CREATE INDEX IF NOT EXISTS idx_clientes_recibe_correos ON clientes(recibe_correos);
CREATE INDEX IF NOT EXISTS idx_clientes_tipo ON clientes(tipo_cliente);

CREATE TRIGGER IF NOT EXISTS trg_clientes_actualiza_fecha
AFTER UPDATE ON clientes
FOR EACH ROW
BEGIN
    UPDATE clientes
    SET fecha_actualizacion = datetime('now')
    WHERE cliente_id = OLD.cliente_id;
END;

-- =========================================================
-- TABLA: plantillas_correo
-- =========================================================
CREATE TABLE IF NOT EXISTS plantillas_correo (
    plantilla_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT NOT NULL UNIQUE,
    asunto          TEXT NOT NULL,
    cuerpo          TEXT NOT NULL,
    activa          INTEGER NOT NULL DEFAULT 1 CHECK (activa IN (0,1)),
    creada_en       TEXT NOT NULL DEFAULT (datetime('now'))
);

-- =========================================================
-- TABLA: campanas
-- =========================================================
CREATE TABLE IF NOT EXISTS campanas (
    campana_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre              TEXT,
    asunto              TEXT NOT NULL,
    cuerpo              TEXT NOT NULL,
    criterio_json       TEXT,
    total_destinatarios INTEGER NOT NULL DEFAULT 0,
    enviados            INTEGER NOT NULL DEFAULT 0,
    fallidos            INTEGER NOT NULL DEFAULT 0,
    creada_en           TEXT NOT NULL DEFAULT (datetime('now'))
);

-- =========================================================
-- TABLA: envios_detalle
-- =========================================================
CREATE TABLE IF NOT EXISTS envios_detalle (
    envio_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    campana_id       INTEGER NOT NULL,
    cliente_id       INTEGER,
    email_destino    TEXT NOT NULL,
    estado           TEXT NOT NULL
                    CHECK (estado IN ('PENDIENTE','ENVIADO','ERROR','OMITIDO'))
                    DEFAULT 'PENDIENTE',
    error_mensaje    TEXT,
    enviado_en       TEXT,

    FOREIGN KEY (campana_id) REFERENCES campanas(campana_id) ON DELETE CASCADE,
    FOREIGN KEY (cliente_id) REFERENCES clientes(cliente_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_envios_campana ON envios_detalle(campana_id);
CREATE INDEX IF NOT EXISTS idx_envios_estado ON envios_detalle(estado);

-- =========================================================
-- TABLA: logs_eventos
-- =========================================================
CREATE TABLE IF NOT EXISTS logs_eventos (
    log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora   TEXT NOT NULL DEFAULT (datetime('now')),
    modulo       TEXT NOT NULL,
    accion       TEXT NOT NULL,
    detalle      TEXT,
    nivel        TEXT NOT NULL DEFAULT 'INFO'
                 CHECK (nivel IN ('INFO','WARN','ERROR'))
);

CREATE INDEX IF NOT EXISTS idx_logs_fecha ON logs_eventos(fecha_hora);
CREATE INDEX IF NOT EXISTS idx_logs_modulo ON logs_eventos(modulo);

-- =========================================================
-- VISTA: vw_clientes_exportacion
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

