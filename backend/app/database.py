"""
Database Management Layer for Contribo
Supports PostgreSQL (via SQLAlchemy) and SQLite fallback.
"""

import json
import time
import logging
from typing import Optional, Dict, Any, Generator

from .config import DATABASE_URL, DATABASE_PATH, CACHE_TTL_SECONDS

logger = logging.getLogger("contribo.database")

# Sample data constants for instant maintainer testing
SAMPLE_KEY = "3cbf75075c9fb159ead33ea4a1557b590d6873ba8c58942da3cde9902c27a8b4"
SAMPLE_PAYLOAD = {
    "cached": False,
    "fetched_at": "2026-10-25T02:00:00Z",
    "issue": {
        "number": 5412,
        "title": "Custom URL converters in blueprints not recognized during endpoint routing",
        "body": "When registering custom URL converters directly onto a Blueprint, URL value parsing does not propagate to url_for...",
        "state": "open",
        "labels": ["bug", "routing"],
        "assignees": [],
        "author": "davidism",
        "url": "https://github.com/pallets/flask/issues/5412"
    },
    "pull_requests": [
        {
            "number": 5415,
            "url": "https://github.com/pallets/flask/pull/5415",
            "title": "Fix blueprint custom URL converter registration and propagation",
            "body": "Fixes #5412 by registering custom converters during blueprint registration.",
            "state": "open",
            "author": "contributor-alice",
            "created_at": "2026-10-20T10:00:00Z",
            "updated_at": "2026-10-24T12:00:00Z",
            "mergeable": True,
            "draft": False,
            "additions": 34,
            "deletions": 4,
            "changed_files_count": 2,
            "files": [
                {
                    "filename": "src/flask/blueprints.py",
                    "status": "modified",
                    "additions": 12,
                    "deletions": 4,
                    "patch": "@@ -188,7 +188,15 @@ def register(self, app, options):\n+        for name, converter in self.url_converters.items():\n+            app.url_map.converters[name] = converter"
                },
                {
                    "filename": "tests/test_blueprints.py",
                    "status": "modified",
                    "additions": 22,
                    "deletions": 0,
                    "patch": "@@ -45,6 +45,28 @@ def test_blueprint_custom_converter(app, client):\n+    bp = Blueprint('api', __name__)\n+    bp.add_url_rule('/<uuid:id>', endpoint='get_item')"
                }
            ],
            "ci_status": {
                "total_checks": 4,
                "state": "success",
                "check_runs": [
                    {"name": "pytest (3.11)", "status": "completed", "conclusion": "success"},
                    {"name": "flake8 linter", "status": "completed", "conclusion": "success"}
                ]
            },
            "error": None
        },
        {
            "number": 5416,
            "url": "https://github.com/pallets/flask/pull/5416",
            "title": "Alternative fix for converter mapping in url_map",
            "body": "Alternative approach to #5412 by modifying global converter lookup.",
            "state": "open",
            "author": "contributor-bob",
            "created_at": "2026-10-21T14:30:00Z",
            "updated_at": "2026-10-24T08:00:00Z",
            "mergeable": True,
            "draft": False,
            "additions": 58,
            "deletions": 21,
            "changed_files_count": 3,
            "files": [
                {
                    "filename": "src/flask/app.py",
                    "status": "modified",
                    "additions": 45,
                    "deletions": 21,
                    "patch": "@@ -310,12 +310,36 @@ def add_url_rule(self, rule, endpoint=None):\n+    # Global converter override"
                },
                {
                    "filename": "tests/test_routing.py",
                    "status": "modified",
                    "additions": 13,
                    "deletions": 0,
                    "patch": "@@ -120,4 +120,17 @@ def test_routing_edge_cases():\n+    pass"
                }
            ],
            "ci_status": {
                "total_checks": 4,
                "state": "failure",
                "check_runs": [
                    {"name": "pytest (3.11)", "status": "completed", "conclusion": "failure"},
                    {"name": "flake8 linter", "status": "completed", "conclusion": "success"}
                ]
            },
            "error": None
        }
    ],
    "warnings": []
}

# Try importing SQLAlchemy; if not installed yet, use sqlite3 fallback
_USE_SQLALCHEMY = False
engine = None
SessionLocal = None
Base = None

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from .models_db import Base, CacheEntry

    # Configure connection pool based on dialect
    connect_args = {}
    if DATABASE_URL.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    engine = create_engine(
        DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    _USE_SQLALCHEMY = True
    logger.info(f"Connected to database via SQLAlchemy: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")
except ImportError:
    import sqlite3
    _USE_SQLALCHEMY = False
    logger.warning("SQLAlchemy not installed in current environment; falling back to direct sqlite3.")


def get_db() -> Generator:
    """FastAPI dependency for obtaining a database session."""
    if _USE_SQLALCHEMY and SessionLocal:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    else:
        yield None


def get_connection():
    """Returns a raw sqlite connection (for legacy / fallback compatibility)."""
    import sqlite3
    db_path = DATABASE_PATH if not DATABASE_URL.startswith("sqlite:///") else DATABASE_URL.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates database tables and seeds sample data."""
    if _USE_SQLALCHEMY and engine and Base:
        try:
            Base.metadata.create_all(bind=engine)
            seed_sample_cache()
            return
        except Exception as e:
            logger.warning(f"SQLAlchemy table creation encountered an error: {e}. Falling back to sqlite3.")

    # SQLite fallback
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                cache_key TEXT PRIMARY KEY,
                response_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            )
        """)
        now = time.time()
        expires_at = now + 86400 * 30
        payload = json.dumps(SAMPLE_PAYLOAD)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO cache_entries (cache_key, response_json, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (SAMPLE_KEY, payload, now, expires_at)
        )
        conn.commit()


def seed_sample_cache():
    """Seeds the sample Flask maintainer data into cache."""
    now = time.time()
    expires_at = now + 86400 * 30  # 30 days

    if _USE_SQLALCHEMY and SessionLocal:
        try:
            with SessionLocal() as session:
                existing = session.query(CacheEntry).filter(CacheEntry.cache_key == SAMPLE_KEY).first()
                if not existing:
                    entry = CacheEntry(
                        cache_key=SAMPLE_KEY,
                        response_json=json.dumps(SAMPLE_PAYLOAD),
                        created_at=now,
                        expires_at=expires_at
                    )
                    session.add(entry)
                    session.commit()
            return
        except Exception as e:
            logger.warning(f"Could not seed sample cache via SQLAlchemy: {e}")

    # Direct SQLite seed
    with get_connection() as conn:
        payload = json.dumps(SAMPLE_PAYLOAD)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO cache_entries (cache_key, response_json, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (SAMPLE_KEY, payload, now, expires_at)
        )
        conn.commit()


def get_cached(key: str) -> Optional[Dict[str, Any]]:
    """Retrieves cached JSON payload if not expired."""
    now = time.time()

    if _USE_SQLALCHEMY and SessionLocal:
        try:
            with SessionLocal() as session:
                entry = session.query(CacheEntry).filter(CacheEntry.cache_key == key).first()
                if entry:
                    if entry.expires_at > now:
                        try:
                            data = json.loads(entry.response_json)
                            data["cached"] = True
                            return data
                        except Exception:
                            return None
                    else:
                        # Expired: delete
                        session.delete(entry)
                        session.commit()
            return None
        except Exception as e:
            logger.debug(f"SQLAlchemy query failed: {e}. Trying fallback.")

    # Direct SQLite query fallback
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT response_json, expires_at FROM cache_entries WHERE cache_key = ?",
            (key,)
        )
        row = cursor.fetchone()
        if row:
            if row["expires_at"] > now:
                try:
                    data = json.loads(row["response_json"])
                    data["cached"] = True
                    return data
                except Exception:
                    return None
            else:
                delete_cached(key)
    return None


def set_cached(key: str, data: Dict[str, Any], ttl_seconds: Optional[int] = None):
    """Sets a cached JSON payload with expiration timestamp."""
    ttl = ttl_seconds if ttl_seconds is not None else CACHE_TTL_SECONDS
    now = time.time()
    expires_at = now + ttl

    data_to_store = dict(data)
    data_to_store["cached"] = False
    payload = json.dumps(data_to_store)

    if _USE_SQLALCHEMY and SessionLocal:
        try:
            with SessionLocal() as session:
                entry = session.query(CacheEntry).filter(CacheEntry.cache_key == key).first()
                if entry:
                    entry.response_json = payload
                    entry.created_at = now
                    entry.expires_at = expires_at
                else:
                    entry = CacheEntry(
                        cache_key=key,
                        response_json=payload,
                        created_at=now,
                        expires_at=expires_at
                    )
                    session.add(entry)
                session.commit()
            return
        except Exception as e:
            logger.debug(f"SQLAlchemy set_cached failed: {e}. Trying fallback.")

    # Direct SQLite set fallback
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO cache_entries (cache_key, response_json, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                response_json = excluded.response_json,
                created_at = excluded.created_at,
                expires_at = excluded.expires_at
            """,
            (key, payload, now, expires_at)
        )
        conn.commit()


def delete_cached(key: str):
    """Deletes a cached payload by key."""
    if _USE_SQLALCHEMY and SessionLocal:
        try:
            with SessionLocal() as session:
                entry = session.query(CacheEntry).filter(CacheEntry.cache_key == key).first()
                if entry:
                    session.delete(entry)
                    session.commit()
            return
        except Exception:
            pass

    # Direct SQLite delete fallback
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache_entries WHERE cache_key = ?", (key,))
        conn.commit()
