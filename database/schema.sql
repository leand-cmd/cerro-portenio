-- =============================================================
-- Schema: Cerro Porteño Scraping Project
-- Motor: PostgreSQL
-- =============================================================

CREATE TABLE IF NOT EXISTS equipos (
    id              SERIAL PRIMARY KEY,
    nombre          VARCHAR(150) NOT NULL UNIQUE,
    pais            VARCHAR(100),
    sofascore_id    INTEGER UNIQUE
);

CREATE TABLE IF NOT EXISTS jugadores (
    id                  SERIAL PRIMARY KEY,
    nombre              VARCHAR(150) NOT NULL,
    posicion            VARCHAR(50),
    equipo_id           INTEGER REFERENCES equipos(id) ON DELETE SET NULL,
    numero              INTEGER,
    fecha_nacimiento    DATE,
    sofascore_id        INTEGER UNIQUE,
    UNIQUE (nombre, equipo_id)
);

CREATE TABLE IF NOT EXISTS partidos (
    id                      SERIAL PRIMARY KEY,
    fecha                   TIMESTAMP NOT NULL,
    equipo_local_id         INTEGER NOT NULL REFERENCES equipos(id) ON DELETE CASCADE,
    equipo_visitante_id     INTEGER NOT NULL REFERENCES equipos(id) ON DELETE CASCADE,
    resultado_local         INTEGER,
    resultado_visitante     INTEGER,
    competicion             VARCHAR(150),
    liga                    VARCHAR(150),
    sofascore_id            INTEGER UNIQUE
);

CREATE TABLE IF NOT EXISTS estadisticas_jugador_partido (
    id                      SERIAL PRIMARY KEY,
    jugador_id              INTEGER NOT NULL REFERENCES jugadores(id) ON DELETE CASCADE,
    partido_id              INTEGER NOT NULL REFERENCES partidos(id) ON DELETE CASCADE,
    calificacion            NUMERIC(3,1),
    minutos                 INTEGER,
    goles                   INTEGER DEFAULT 0,
    asistencias             INTEGER DEFAULT 0,
    tarjetas_amarillas      INTEGER DEFAULT 0,
    tarjetas_rojas          INTEGER DEFAULT 0,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (jugador_id, partido_id)
);

CREATE TABLE IF NOT EXISTS estadisticas_partido (
    id              SERIAL PRIMARY KEY,
    partido_id      INTEGER NOT NULL REFERENCES partidos(id) ON DELETE CASCADE,
    equipo_id       INTEGER NOT NULL REFERENCES equipos(id) ON DELETE CASCADE,
    posesion        NUMERIC(5,2),
    tiros_porteria  INTEGER,
    faltas          INTEGER,
    corner          INTEGER,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (partido_id, equipo_id)
);

-- Índices para las consultas más frecuentes (por jugador y por fecha)
CREATE INDEX IF NOT EXISTS idx_partidos_fecha ON partidos (fecha);
CREATE INDEX IF NOT EXISTS idx_estadisticas_jugador_partido_jugador_id ON estadisticas_jugador_partido (jugador_id);
CREATE INDEX IF NOT EXISTS idx_estadisticas_jugador_partido_partido_id ON estadisticas_jugador_partido (partido_id);
CREATE INDEX IF NOT EXISTS idx_estadisticas_partido_partido_id ON estadisticas_partido (partido_id);
CREATE INDEX IF NOT EXISTS idx_jugadores_equipo_id ON jugadores (equipo_id);
