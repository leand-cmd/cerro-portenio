"""
Manejo de la conexión a PostgreSQL usando psycopg2.
"""
import logging
from typing import Optional
import os

import psycopg2
from psycopg2.extensions import connection as PGConnection

logger = logging.getLogger(__name__)

_connection: Optional[PGConnection] = None


def conectar() -> Optional[PGConnection]:
    """
    Abre una nueva conexión a PostgreSQL.
    Usa DATABASE_URL (Railway) o variables individuales (.env local).
    """
    try:
        db_url = os.getenv('DATABASE_URL')
        
        if db_url:
            # Railway: usa DATABASE_URL directamente
            conn = psycopg2.connect(db_url)
            logger.info("✓ Conectado a PostgreSQL (Railway)")
        else:
            # Local: usa variables individuales
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', ''),
                dbname=os.getenv('DB_NAME', 'cerro_data'),
                port=os.getenv('DB_PORT', '5432'),
            )
            logger.info("✓ Conectado a PostgreSQL (Local)")
        
        return conn
    except psycopg2.OperationalError as e:
        logger.error("❌ Error de conexión: %s", e)
        return None
    except Exception as e:
        logger.error("❌ Error inesperado: %s", e)
        return None


def get_connection() -> PGConnection:
    """Devuelve una conexión reutilizable."""
    global _connection
    if _connection is None or _connection.closed:
        _connection = conectar()
        if _connection is None:
            raise ConnectionError("No se pudo conectar a PostgreSQL")
    return _connection


def cerrar_conexion() -> None:
    """Cierra la conexión."""
    global _connection
    if _connection is not None and not _connection.closed:
        _connection.close()
        logger.info("✓ Conexión cerrada")
    _connection = None


def inicializar_schema(schema_path: str = "database/schema.sql") -> None:
    """Ejecuta el schema.sql."""
    conn = get_connection()
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        conn.commit()
        logger.info("✓ Schema inicializado")
    except Exception as e:
        conn.rollback()
        logger.error("❌ Error en schema: %s", e)
        raise