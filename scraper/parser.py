"""
Limpieza y normalización de los datos crudos extraídos de SofaScore
antes de insertarlos en PostgreSQL.
"""
import logging
import re
import unicodedata
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def _normalizar_texto(texto: Optional[str]) -> Optional[str]:
    """Recorta espacios y colapsa espacios múltiples. Preserva tildes/ñ."""
    if texto is None:
        return None
    texto = unicodedata.normalize("NFC", str(texto)).strip()
    texto = re.sub(r"\s+", " ", texto)
    return texto or None


def _a_int(valor) -> Optional[int]:
    """Convierte a int de forma segura; retorna None si no es posible."""
    if valor is None or valor == "":
        return None
    try:
        return int(float(valor))
    except (ValueError, TypeError):
        return None


def _a_float(valor) -> Optional[float]:
    """Convierte a float de forma segura; retorna None si no es posible."""
    if valor is None or valor == "":
        return None
    try:
        return round(float(valor), 2)
    except (ValueError, TypeError):
        return None


def _timestamp_a_fecha(timestamp) -> Optional[str]:
    """Convierte un timestamp UNIX (segundos) al formato ISO que espera PostgreSQL."""
    if timestamp is None:
        return None
    try:
        return datetime.utcfromtimestamp(int(timestamp)).isoformat()
    except (ValueError, TypeError, OSError):
        return None


def _limpiar_jugador(jugador_crudo: dict) -> Optional[dict]:
    """Normaliza y valida un jugador. Retorna None si faltan datos críticos."""
    nombre = _normalizar_texto(jugador_crudo.get("nombre"))
    equipo = _normalizar_texto(jugador_crudo.get("equipo"))

    if not nombre or not equipo:
        logger.warning("Jugador descartado por datos críticos faltantes: %s", jugador_crudo)
        return None

    return {
        "nombre": nombre,
        "posicion": _normalizar_texto(jugador_crudo.get("posicion")),
        "numero": _a_int(jugador_crudo.get("numero")),
        "equipo": equipo,
        "calificacion": _a_float(jugador_crudo.get("calificacion")),
        "minutos": _a_int(jugador_crudo.get("minutos")) or 0,
        "goles": _a_int(jugador_crudo.get("goles")) or 0,
        "asistencias": _a_int(jugador_crudo.get("asistencias")) or 0,
        "tarjetas_amarillas": _a_int(jugador_crudo.get("tarjetas_amarillas")) or 0,
        "tarjetas_rojas": _a_int(jugador_crudo.get("tarjetas_rojas")) or 0,
    }


def _limpiar_estadistica_equipo(stat_crudo: dict) -> Optional[dict]:
    """Normaliza y valida estadísticas de equipo de un partido."""
    equipo = _normalizar_texto(stat_crudo.get("equipo"))
    if not equipo:
        return None
    return {
        "equipo": equipo,
        "posesion": _a_float(stat_crudo.get("posesion")),
        "tiros_porteria": _a_int(stat_crudo.get("tiros_porteria")),
        "faltas": _a_int(stat_crudo.get("faltas")),
        "corner": _a_int(stat_crudo.get("corner")),
    }


def limpiar_datos(partidos_crudos: list[dict]) -> list[dict]:
    """
    Toma la lista de partidos crudos devuelta por scrape_cerro_portenio()
    y retorna una lista limpia y validada, lista para insertar en la BD.

    Descarta partidos sin los campos críticos (fecha, equipos, id de SofaScore)
    y descarta jugadores individuales con datos incompletos, sin descartar
    el partido completo.
    """
    partidos_limpios = []

    for partido in partidos_crudos:
        sofascore_id = _a_int(partido.get("sofascore_id"))
        fecha = _timestamp_a_fecha(partido.get("fecha"))
        equipo_local = _normalizar_texto(partido.get("equipo_local"))
        equipo_visitante = _normalizar_texto(partido.get("equipo_visitante"))

        if not sofascore_id or not fecha or not equipo_local or not equipo_visitante:
            logger.warning(
                "Partido descartado por datos críticos faltantes (sofascore_id=%s)",
                partido.get("sofascore_id"),
            )
            continue

        jugadores_limpios = [
            j for j in (_limpiar_jugador(j) for j in partido.get("jugadores", [])) if j is not None
        ]
        estadisticas_limpias = [
            s for s in (_limpiar_estadistica_equipo(s) for s in partido.get("estadisticas_equipo", [])) if s is not None
        ]

        partidos_limpios.append(
            {
                "sofascore_id": sofascore_id,
                "fecha": fecha,
                "equipo_local": equipo_local,
                "equipo_visitante": equipo_visitante,
                "resultado_local": _a_int(partido.get("resultado_local")),
                "resultado_visitante": _a_int(partido.get("resultado_visitante")),
                "competicion": _normalizar_texto(partido.get("competicion")),
                "liga": _normalizar_texto(partido.get("liga")),
                "jugadores": jugadores_limpios,
                "estadisticas_equipo": estadisticas_limpias,
            }
        )

    logger.info("Limpieza completada: %d/%d partidos válidos", len(partidos_limpios), len(partidos_crudos))
    return partidos_limpios
