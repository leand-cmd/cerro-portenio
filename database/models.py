"""
Funciones de inserción (INSERT) para cada tabla del schema.
Todas manejan duplicados y retornan el id del registro insertado o existente.
"""
import logging

from database.connection import get_connection

logger = logging.getLogger(__name__)


def insert_equipo(nombre: str, pais: str = None, sofascore_id: int = None) -> int:
    """Inserta un equipo o retorna el id existente (por nombre)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO equipos (nombre, pais, sofascore_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (nombre) DO UPDATE SET nombre = EXCLUDED.nombre
                RETURNING id
                """,
                (nombre, pais, sofascore_id),
            )
            equipo_id = cur.fetchone()[0]
        conn.commit()
        logger.info("Equipo insertado/existente: %s (id=%s)", nombre, equipo_id)
        return equipo_id
    except Exception as e:
        conn.rollback()
        logger.error("Error al insertar equipo '%s': %s", nombre, e)
        raise


def insert_jugador(
    nombre: str,
    posicion: str,
    equipo_id: int,
    numero: int = None,
    fecha_nacimiento: str = None,
    sofascore_id: int = None,
) -> int:
    """Inserta un jugador o retorna el id existente (por nombre + equipo)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO jugadores (nombre, posicion, equipo_id, numero, fecha_nacimiento, sofascore_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (nombre, equipo_id) DO UPDATE SET
                    posicion = COALESCE(EXCLUDED.posicion, jugadores.posicion),
                    numero = COALESCE(EXCLUDED.numero, jugadores.numero)
                RETURNING id
                """,
                (nombre, posicion, equipo_id, numero, fecha_nacimiento, sofascore_id),
            )
            jugador_id = cur.fetchone()[0]
        conn.commit()
        logger.info("Jugador insertado/existente: %s (id=%s)", nombre, jugador_id)
        return jugador_id
    except Exception as e:
        conn.rollback()
        logger.error("Error al insertar jugador '%s': %s", nombre, e)
        raise


def insert_partido(
    fecha: str,
    equipo_local_id: int,
    equipo_visitante_id: int,
    resultado_local: int,
    resultado_visitante: int,
    competicion: str = None,
    liga: str = None,
    sofascore_id: int = None,
) -> int:
    """Inserta un partido o retorna el id existente (por sofascore_id)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if sofascore_id is not None:
                cur.execute(
                    """
                    INSERT INTO partidos (
                        fecha, equipo_local_id, equipo_visitante_id,
                        resultado_local, resultado_visitante, competicion, liga, sofascore_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (sofascore_id) DO UPDATE SET
                        resultado_local = EXCLUDED.resultado_local,
                        resultado_visitante = EXCLUDED.resultado_visitante
                    RETURNING id
                    """,
                    (
                        fecha,
                        equipo_local_id,
                        equipo_visitante_id,
                        resultado_local,
                        resultado_visitante,
                        competicion,
                        liga,
                        sofascore_id,
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO partidos (
                        fecha, equipo_local_id, equipo_visitante_id,
                        resultado_local, resultado_visitante, competicion, liga
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        fecha,
                        equipo_local_id,
                        equipo_visitante_id,
                        resultado_local,
                        resultado_visitante,
                        competicion,
                        liga,
                    ),
                )
            partido_id = cur.fetchone()[0]
        conn.commit()
        logger.info("Partido insertado/existente: id=%s (sofascore_id=%s)", partido_id, sofascore_id)
        return partido_id
    except Exception as e:
        conn.rollback()
        logger.error("Error al insertar partido (sofascore_id=%s): %s", sofascore_id, e)
        raise


def insert_estadisticas_jugador(
    jugador_id: int,
    partido_id: int,
    calificacion: float,
    minutos: int,
    goles: int = 0,
    asistencias: int = 0,
    tarjetas_amarillas: int = 0,
    tarjetas_rojas: int = 0,
) -> int:
    """Inserta estadísticas de un jugador en un partido, o actualiza si ya existe."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO estadisticas_jugador_partido (
                    jugador_id, partido_id, calificacion, minutos,
                    goles, asistencias, tarjetas_amarillas, tarjetas_rojas
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (jugador_id, partido_id) DO UPDATE SET
                    calificacion = EXCLUDED.calificacion,
                    minutos = EXCLUDED.minutos,
                    goles = EXCLUDED.goles,
                    asistencias = EXCLUDED.asistencias,
                    tarjetas_amarillas = EXCLUDED.tarjetas_amarillas,
                    tarjetas_rojas = EXCLUDED.tarjetas_rojas
                RETURNING id
                """,
                (
                    jugador_id,
                    partido_id,
                    calificacion,
                    minutos,
                    goles,
                    asistencias,
                    tarjetas_amarillas,
                    tarjetas_rojas,
                ),
            )
            stat_id = cur.fetchone()[0]
        conn.commit()
        logger.info(
            "Estadísticas insertadas: jugador_id=%s partido_id=%s (id=%s)",
            jugador_id, partido_id, stat_id,
        )
        return stat_id
    except Exception as e:
        conn.rollback()
        logger.error(
            "Error al insertar estadísticas (jugador_id=%s, partido_id=%s): %s",
            jugador_id, partido_id, e,
        )
        raise


def insert_estadisticas_partido(
    partido_id: int,
    equipo_id: int,
    posesion: float = None,
    tiros_porteria: int = None,
    faltas: int = None,
    corner: int = None,
) -> int:
    """Inserta estadísticas de equipo en un partido, o actualiza si ya existe."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO estadisticas_partido (
                    partido_id, equipo_id, posesion, tiros_porteria, faltas, corner
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (partido_id, equipo_id) DO UPDATE SET
                    posesion = EXCLUDED.posesion,
                    tiros_porteria = EXCLUDED.tiros_porteria,
                    faltas = EXCLUDED.faltas,
                    corner = EXCLUDED.corner
                RETURNING id
                """,
                (partido_id, equipo_id, posesion, tiros_porteria, faltas, corner),
            )
            stat_id = cur.fetchone()[0]
        conn.commit()
        logger.info(
            "Estadísticas de equipo insertadas: equipo_id=%s partido_id=%s (id=%s)",
            equipo_id, partido_id, stat_id,
        )
        return stat_id
    except Exception as e:
        conn.rollback()
        logger.error(
            "Error al insertar estadísticas de equipo (partido_id=%s, equipo_id=%s): %s",
            partido_id, equipo_id, e,
        )
        raise
