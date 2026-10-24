"""
Contribo Database Migration Runner
Applies schema migrations to PostgreSQL or the configured DATABASE_URL.
"""

import sys
import os
import logging

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.config import DATABASE_URL
from backend.app.database import init_db, _USE_SQLALCHEMY, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("contribo.migrate")


def run_migrations():
    masked_url = DATABASE_URL
    if "@" in masked_url:
        protocol_and_auth, host_and_db = masked_url.split("@", 1)
        protocol = protocol_and_auth.split("://")[0]
        masked_url = f"{protocol}://****:****@{host_and_db}"

    logger.info(f"Target Database: {masked_url}")

    # Check if alembic is available
    try:
        from alembic.config import Config
        from alembic import command

        alembic_ini_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini"))
        if os.path.exists(alembic_ini_path):
            logger.info("Running Alembic migrations (upgrade head)...")
            alembic_cfg = Config(alembic_ini_path)
            alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
            command.upgrade(alembic_cfg, "head")
            logger.info("Alembic migrations completed successfully.")
            return
    except ImportError:
        logger.info("Alembic not installed; applying schema via SQLAlchemy/DDL directly...")
    except Exception as e:
        logger.warning(f"Alembic migration failed ({e}); falling back to init_db()...")

    # Fallback to direct init_db()
    init_db()
    logger.info("Database schema initialized successfully.")


if __name__ == "__main__":
    run_migrations()
