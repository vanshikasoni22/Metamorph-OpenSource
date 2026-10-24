"""
SQLite to PostgreSQL Data Migration Script
Copies cached entries and records from local SQLite to PostgreSQL.
Usage:
    python3 -m backend.scripts.sqlite_to_postgres
"""

import sys
import os
import sqlite3
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.config import DATABASE_URL, DATABASE_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("contribo.sqlite_to_postgres")


def migrate_data():
    if not os.path.exists(DATABASE_PATH):
        logger.info(f"No existing SQLite database found at {DATABASE_PATH}. Nothing to migrate.")
        return

    if not DATABASE_URL.startswith("postgresql"):
        logger.warning(f"DATABASE_URL is not PostgreSQL: {DATABASE_URL}. Set DATABASE_URL in .env before running data migration.")
        return

    logger.info(f"Reading from SQLite: {DATABASE_PATH}")
    sqlite_conn = sqlite3.connect(DATABASE_PATH)
    sqlite_conn.row_factory = sqlite3.Row

    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from backend.app.models_db import CacheEntry

        pg_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        PgSession = sessionmaker(bind=pg_engine)

        cursor = sqlite_conn.cursor()
        cursor.execute("SELECT cache_key, response_json, created_at, expires_at FROM cache_entries")
        rows = cursor.fetchall()

        logger.info(f"Found {len(rows)} cache row(s) in SQLite.")

        with PgSession() as pg_session:
            migrated_count = 0
            for r in rows:
                existing = pg_session.query(CacheEntry).filter(CacheEntry.cache_key == r["cache_key"]).first()
                if not existing:
                    entry = CacheEntry(
                        cache_key=r["cache_key"],
                        response_json=r["response_json"],
                        created_at=r["created_at"],
                        expires_at=r["expires_at"]
                    )
                    pg_session.add(entry)
                    migrated_count += 1
            pg_session.commit()
            logger.info(f"Successfully migrated {migrated_count} new row(s) to PostgreSQL.")

    except ImportError:
        logger.error("SQLAlchemy or psycopg2 is not installed. Run: pip install -r backend/requirements.txt")
    except Exception as e:
        logger.error(f"Migration error: {e}")
    finally:
        sqlite_conn.close()


if __name__ == "__main__":
    migrate_data()
