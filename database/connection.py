"""
Manejo de la conexión a PostgreSQL usando psycopg2.
"""
import logging
from typing import Optional

import psycopg2
from psycopg2.extensions import connection as PGConnection

import config

logger = logging.getLogger(__name__)

_connection: Optional[PGConnection] = None


def conectar() -> Optional[PGConnection]:
    """
    Abre una nueva conexión a PostgreSQL usando las variables de entorno
    definidas en config.py (leídas desde .env).

    Retorna la conexión o None si falla.
    """
    try:
        conn = psycopg2.connect(
            host=config.DB_HOST,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            dbname=config.DB_NAME,
            port=config.DB_PORT,
        )
        logger.info("✓ Conexión a PostgreSQL establecida (db=%s, host=%s)", config.DB_NAME, config.DB_HOST)
        return conn
    except psycopg2.OperationalError as e:
        logger.error("❌ Error de conexión a PostgreSQL: %s", e)
        return None
    except Exception as e:
        logger.error("❌ Error inesperado al conectar a PostgreSQL: %s", e)
        return None


def get_connection() -> PGConnection:
    """
    Devuelve una conexión reutilizable (singleton a nivel de módulo).
    Si la conexión está cerrada o no existe, crea una nueva.
    """
    global _connection
    if _connection is None or _connection.closed:
        _connection = conectar()
        if _connection is None:
            raise ConnectionError("No se pudo establecer conexión con PostgreSQL")
    return _connection


def cerrar_conexion() -> None:
    """Cierra la conexión reutilizable si está abierta."""
    global _connection
    if _connection is not None and not _connection.closed:
        _connection.close()
        logger.info("✓ Conexión a PostgreSQL cerrada")
    _connection = None


def inicializar_schema(schema_path: str = "database/schema.sql") -> None:
    """Ejecuta el schema.sql para crear las tablas si no existen."""
    conn = get_connection()
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()
        logger.info("✓ Schema inicializado correctamente")
    except Exception as e:
        conn.rollback()
        logger.error("❌ Error al inicializar el schema: %s", e)
        raise