import sqlite3
import json
import time
from typing import Optional, Dict, Any
from .config import DATABASE_PATH, CACHE_TTL_SECONDS

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                cache_key TEXT PRIMARY KEY,
                response_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            )
        """)
        conn.commit()

def get_cached(key: str) -> Optional[Dict[str, Any]]:
    now = time.time()
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
                # Expired: clean it up
                delete_cached(key)
    return None

def set_cached(key: str, data: Dict[str, Any], ttl_seconds: Optional[int] = None):
    ttl = ttl_seconds if ttl_seconds is not None else CACHE_TTL_SECONDS
    now = time.time()
    expires_at = now + ttl
    # Ensure cached flag is False when stored in database
    data_to_store = dict(data)
    data_to_store["cached"] = False
    payload = json.dumps(data_to_store)

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
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache_entries WHERE cache_key = ?", (key,))
        conn.commit()
