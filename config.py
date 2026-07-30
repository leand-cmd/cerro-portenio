"""
Configuración centralizada del proyecto: URLs, IDs, delays y logging.
"""
import logging
import os

from dotenv import load_dotenv

load_dotenv()

# --- SofaScore ---
URL_SOFASCORE = "https://www.sofascore.com"
URL_SOFASCORE_API = "https://api.sofascore.com/api/v1"

# ID del equipo Cerro Porteño en SofaScore (team/cerro-porteno/2914)
CERRO_PORTENIO_ID = 2914
CERRO_PORTENIO_SLUG = "cerro-porteno"

# Cantidad de partidos recientes a extraer
PARTIDOS_A_EXTRAER = 20

# --- Delays / rate limiting ---
DELAY_MIN_SEGUNDOS = 2
DELAY_MAX_SEGUNDOS = 3

# User-Agent realista para Playwright
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# --- Base de datos ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "cerro_data")
DB_PORT = os.getenv("DB_PORT", "5432")

# --- Logging ---
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "scraper.log")


def configurar_logging():
    """Configura logging a consola y archivo, nivel INFO."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
