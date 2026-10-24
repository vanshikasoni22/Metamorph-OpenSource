import sqlite3
import json
import time
from typing import Optional, Dict, Any
from .config import DATABASE_PATH, CACHE_TTL_SECONDS

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def seed_sample_cache(conn: sqlite3.Connection):
    sample_key = "3cbf75075c9fb159ead33ea4a1557b590d6873ba8c58942da3cde9902c27a8b4"
    now = time.time()
    expires_at = now + 86400 * 30  # 30 days
    sample_payload = json.dumps({
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
    })
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO cache_entries (cache_key, response_json, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        (sample_key, sample_payload, now, expires_at)
    )

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
        seed_sample_cache(conn)
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
