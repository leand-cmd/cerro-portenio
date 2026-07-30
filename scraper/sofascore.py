"""
Scraper de SofaScore para el equipo Cerro Porteño.

Estrategia: SofaScore es una SPA que obtiene sus datos desde
api.sofascore.com. En vez de parsear HTML/CSS (frágil y cambia
constantemente), usamos Playwright para abrir el sitio real (con un
User-Agent y navegador reales) y usamos su mismo contexto de red
(APIRequestContext) para pedir los endpoints JSON que la propia página
consume. Esto es más estable y devuelve datos ya estructurados.

Endpoints utilizados:
- /api/v1/search/all?q=...                     -> resolver el equipo
- /api/v1/team/{id}/events/last/{page}          -> últimos partidos
- /api/v1/event/{event_id}/lineups              -> jugadores + calificaciones
- /api/v1/event/{event_id}/statistics           -> posesión, tiros, faltas, corners
"""
import logging
import random
import time
from typing import Optional

from playwright.sync_api import sync_playwright

import config

logger = logging.getLogger(__name__)


def _delay():
    """Espera aleatoria entre DELAY_MIN_SEGUNDOS y DELAY_MAX_SEGUNDOS para no saturar SofaScore."""
    tiempo = random.uniform(config.DELAY_MIN_SEGUNDOS, config.DELAY_MAX_SEGUNDOS)
    time.sleep(tiempo)


def _get_json(request_context, url: str) -> Optional[dict]:
    """Realiza un GET y retorna el JSON, o None si falla (con logging del error)."""
    try:
        response = request_context.get(url)
        if response.ok:
            return response.json()
        logger.warning("Respuesta no OK (%s) para %s", response.status, url)
        return None
    except Exception as e:
        logger.error("Error al pedir %s: %s", url, e)
        return None


def _resolver_equipo_id(request_context) -> Optional[int]:
    """
    Busca 'Cerro Porteño' en el buscador de SofaScore para confirmar/obtener
    su team id. Si falla, cae de vuelta al id configurado en config.py.
    """
    url = f"{config.URL_SOFASCORE_API}/search/all?q=Cerro%20Porteno"
    data = _get_json(request_context, url)
    if data:
        for resultado in data.get("results", []):
            entidad = resultado.get("entity", {})
            if resultado.get("type") == "team" and "cerro" in entidad.get("name", "").lower():
                logger.info("Equipo resuelto vía búsqueda: %s (id=%s)", entidad.get("name"), entidad.get("id"))
                return entidad.get("id")
    logger.warning(
        "No se pudo resolver el equipo por búsqueda, usando CERRO_PORTENIO_ID de config.py (%s)",
        config.CERRO_PORTENIO_ID,
    )
    return config.CERRO_PORTENIO_ID


def _extraer_partidos_recientes(request_context, equipo_id: int, cantidad: int) -> list[dict]:
    """Obtiene los últimos `cantidad` eventos (partidos) finalizados del equipo."""
    eventos = []
    pagina = 0
    while len(eventos) < cantidad:
        url = f"{config.URL_SOFASCORE_API}/team/{equipo_id}/events/last/{pagina}"
        data = _get_json(request_context, url)
        _delay()
        if not data or not data.get("events"):
            break
        eventos.extend(data["events"])
        if not data.get("hasNextPage"):
            break
        pagina += 1
    return eventos[:cantidad]


def _mapear_estadisticas_equipo(stats_data: dict, nombre_local: str, nombre_visitante: str) -> list[dict]:
    """Extrae posesión, tiros al arco, faltas y corners desde /event/{id}/statistics."""
    resultado = []
    if not stats_data:
        return resultado

    try:
        periodo_general = next(
            (p for p in stats_data.get("statistics", []) if p.get("period") == "ALL"), None
        )
        if not periodo_general:
            return resultado

        valores = {"home": {}, "away": {}}
        for grupo in periodo_general.get("groups", []):
            for item in grupo.get("statisticsItems", []):
                nombre = item.get("name", "").lower()
                if "possession" in nombre:
                    valores["home"]["posesion"] = item.get("homeValue")
                    valores["away"]["posesion"] = item.get("awayValue")
                elif "shots on target" in nombre:
                    valores["home"]["tiros_porteria"] = item.get("homeValue")
                    valores["away"]["tiros_porteria"] = item.get("awayValue")
                elif nombre == "fouls":
                    valores["home"]["faltas"] = item.get("homeValue")
                    valores["away"]["faltas"] = item.get("awayValue")
                elif "corner" in nombre:
                    valores["home"]["corner"] = item.get("homeValue")
                    valores["away"]["corner"] = item.get("awayValue")

        resultado.append({"equipo": nombre_local, **valores["home"]})
        resultado.append({"equipo": nombre_visitante, **valores["away"]})
    except Exception as e:
        logger.warning("No se pudieron mapear estadísticas de equipo: %s", e)

    return resultado


def _mapear_jugadores(lineups_data: dict, nombre_local: str, nombre_visitante: str) -> list[dict]:
    """Extrae jugadores con calificación, minutos, goles, asistencias y tarjetas."""
    jugadores = []
    if not lineups_data:
        return jugadores

    lados = {"home": nombre_local, "away": nombre_visitante}
    for lado, nombre_equipo in lados.items():
        bloque = lineups_data.get(lado, {})
        for entrada in bloque.get("players", []):
            jugador = entrada.get("player", {})
            stats = entrada.get("statistics", {}) or {}
            jugadores.append(
                {
                    "nombre": jugador.get("name"),
                    "posicion": jugador.get("position"),
                    "numero": jugador.get("jerseyNumber"),
                    "equipo": nombre_equipo,
                    "calificacion": stats.get("rating"),
                    "minutos": stats.get("minutesPlayed"),
                    "goles": stats.get("goals", 0),
                    "asistencias": stats.get("goalAssist", 0),
                    "tarjetas_amarillas": 1 if stats.get("yellowCards") else 0,
                    "tarjetas_rojas": 1 if stats.get("redCards") else 0,
                }
            )
    return jugadores


def scrape_cerro_portenio() -> list[dict]:
    """
    Scrapea los últimos partidos de Cerro Porteño en SofaScore: resultado,
    rival, competición y estadísticas por jugador (calificación, minutos,
    goles, asistencias, tarjetas).

    Retorna una lista de diccionarios "crudos" (listos para limpiar_datos()).
    Es resiliente: si un partido individual falla, se omite y se continúa
    con los siguientes.
    """
    partidos_extraidos = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        contexto = browser.new_context(
            user_agent=config.USER_AGENT,
            extra_http_headers={
                "Referer": config.URL_SOFASCORE,
                "Accept": "application/json",
            },
        )
        page = contexto.new_page()

        try:
            # Visitamos el sitio real primero para simular navegación humana
            # y obtener cookies válidas antes de golpear la API.
            page.goto(config.URL_SOFASCORE, wait_until="domcontentloaded", timeout=30000)
            _delay()

            equipo_id = _resolver_equipo_id(contexto.request)
            if not equipo_id:
                logger.error("No se pudo determinar el ID de Cerro Porteño, abortando scraping")
                return []

            eventos = _extraer_partidos_recientes(contexto.request, equipo_id, config.PARTIDOS_A_EXTRAER)
            logger.info("Se encontraron %d partidos recientes", len(eventos))

            for evento in eventos:
                try:
                    event_id = evento.get("id")
                    nombre_local = evento.get("homeTeam", {}).get("name")
                    nombre_visitante = evento.get("awayTeam", {}).get("name")
                    torneo = evento.get("tournament", {})

                    partido = {
                        "sofascore_id": event_id,
                        "fecha": evento.get("startTimestamp"),
                        "equipo_local": nombre_local,
                        "equipo_visitante": nombre_visitante,
                        "resultado_local": evento.get("homeScore", {}).get("current"),
                        "resultado_visitante": evento.get("awayScore", {}).get("current"),
                        "competicion": torneo.get("name"),
                        "liga": torneo.get("uniqueTournament", {}).get("name") if torneo.get("uniqueTournament") else torneo.get("name"),
                        "jugadores": [],
                        "estadisticas_equipo": [],
                    }

                    lineups = _get_json(contexto.request, f"{config.URL_SOFASCORE_API}/event/{event_id}/lineups")
                    _delay()
                    partido["jugadores"] = _mapear_jugadores(lineups, nombre_local, nombre_visitante)

                    stats = _get_json(contexto.request, f"{config.URL_SOFASCORE_API}/event/{event_id}/statistics")
                    _delay()
                    partido["estadisticas_equipo"] = _mapear_estadisticas_equipo(stats, nombre_local, nombre_visitante)

                    partidos_extraidos.append(partido)
                    logger.info(
                        "Partido procesado: %s vs %s (id=%s) - %d jugadores",
                        nombre_local, nombre_visitante, event_id, len(partido["jugadores"]),
                    )
                except Exception as e:
                    logger.error("Error procesando partido id=%s: %s", evento.get("id"), e)
                    continue

        except Exception as e:
            logger.error("Error general durante el scraping: %s", e)
        finally:
            contexto.close()
            browser.close()

    return partidos_extraidos
