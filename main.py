"""
Orquesta el flujo completo: scraping de SofaScore -> limpieza -> inserción en PostgreSQL.

Uso:
    python main.py
"""
import logging

import config
from database.connection import cerrar_conexion, get_connection, inicializar_schema
from database.models import (
    insert_equipo,
    insert_estadisticas_jugador,
    insert_estadisticas_partido,
    insert_jugador,
    insert_partido,
)
from scraper.parser import limpiar_datos
from scraper.sofascore import scrape_cerro_portenio

config.configurar_logging()
logger = logging.getLogger(__name__)

PAIS_EQUIPO_DEFAULT = "Paraguay"


def _procesar_partido(partido: dict, resumen: dict) -> None:
    """Inserta un partido limpio (y sus jugadores/estadísticas) en la BD."""
    equipo_local_id = insert_equipo(partido["equipo_local"], PAIS_EQUIPO_DEFAULT)
    equipo_visitante_id = insert_equipo(partido["equipo_visitante"], PAIS_EQUIPO_DEFAULT)

    ids_equipo_por_nombre = {
        partido["equipo_local"]: equipo_local_id,
        partido["equipo_visitante"]: equipo_visitante_id,
    }

    partido_id = insert_partido(
        fecha=partido["fecha"],
        equipo_local_id=equipo_local_id,
        equipo_visitante_id=equipo_visitante_id,
        resultado_local=partido["resultado_local"],
        resultado_visitante=partido["resultado_visitante"],
        competicion=partido["competicion"],
        liga=partido["liga"],
        sofascore_id=partido["sofascore_id"],
    )
    resumen["partidos"] += 1

    for jugador in partido["jugadores"]:
        equipo_id = ids_equipo_por_nombre.get(jugador["equipo"])
        if equipo_id is None:
            logger.warning("Jugador '%s' con equipo desconocido '%s', se omite", jugador["nombre"], jugador["equipo"])
            continue

        jugador_id = insert_jugador(
            nombre=jugador["nombre"],
            posicion=jugador["posicion"],
            equipo_id=equipo_id,
            numero=jugador["numero"],
        )
        resumen["jugadores"].add(jugador_id)

        insert_estadisticas_jugador(
            jugador_id=jugador_id,
            partido_id=partido_id,
            calificacion=jugador["calificacion"],
            minutos=jugador["minutos"],
            goles=jugador["goles"],
            asistencias=jugador["asistencias"],
            tarjetas_amarillas=jugador["tarjetas_amarillas"],
            tarjetas_rojas=jugador["tarjetas_rojas"],
        )
        resumen["estadisticas"] += 1

    for stat_equipo in partido["estadisticas_equipo"]:
        equipo_id = ids_equipo_por_nombre.get(stat_equipo["equipo"])
        if equipo_id is None:
            continue
        insert_estadisticas_partido(
            partido_id=partido_id,
            equipo_id=equipo_id,
            posesion=stat_equipo["posesion"],
            tiros_porteria=stat_equipo["tiros_porteria"],
            faltas=stat_equipo["faltas"],
            corner=stat_equipo["corner"],
        )


def main() -> None:
    resumen = {"partidos": 0, "jugadores": set(), "estadisticas": 0}

    logger.info("=== Iniciando pipeline de scraping Cerro Porteño (SofaScore) ===")

    conn = get_connection()
    if conn is None:
        logger.error("No se pudo conectar a PostgreSQL. Abortando.")
        return

    try:
        inicializar_schema()
    except Exception:
        logger.error("No se pudo inicializar el schema. Abortando.")
        return

    logger.info("Iniciando scraping de SofaScore...")
    try:
        partidos_crudos = scrape_cerro_portenio()
    except Exception as e:
        logger.error("El scraping falló: %s", e)
        return

    if not partidos_crudos:
        logger.warning("El scraper no devolvió partidos. Finalizando sin insertar datos.")
        return

    logger.info("Limpiando y validando datos extraídos...")
    partidos_limpios = limpiar_datos(partidos_crudos)

    if not partidos_limpios:
        logger.warning("Ningún partido pasó la validación de limpieza. Finalizando.")
        return

    logger.info("Insertando %d partidos en PostgreSQL...", len(partidos_limpios))
    for partido in partidos_limpios:
        try:
            _procesar_partido(partido, resumen)
        except Exception as e:
            conn.rollback()
            logger.error("Falló la inserción del partido sofascore_id=%s: %s. Se hizo rollback y se continúa.", partido.get("sofascore_id"), e)
            continue

    logger.info(
        "✓ %d partidos insertados, %d jugadores, %d estadísticas",
        resumen["partidos"], len(resumen["jugadores"]), resumen["estadisticas"],
    )
    print(
        f"✓ {resumen['partidos']} partidos insertados, "
        f"{len(resumen['jugadores'])} jugadores, "
        f"{resumen['estadisticas']} estadísticas"
    )


if __name__ == "__main__":
    try:
        main()
    finally:
        cerrar_conexion()
