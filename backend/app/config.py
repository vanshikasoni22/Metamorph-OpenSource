import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger("contribo.config")

# GITHUB_TOKEN: never logged, read safely from environment
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip() or None

if not GITHUB_TOKEN:
    logger.warning(
        "WARNING: GITHUB_TOKEN not found in environment. "
        "Operating in unauthenticated mode (rate limit: 60 requests/hour). "
        "Set GITHUB_TOKEN in .env or environment to unlock 5,000 requests/hour."
    )

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "600"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "contrib_cache.db")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# Database connection URL (PostgreSQL / SQLite)
# Normalizes Render/Heroku 'postgres://' URI to 'postgresql://' for SQLAlchemy
raw_db_url = os.getenv("DATABASE_URL", "").strip()
if raw_db_url:
    if raw_db_url.startswith("postgres://"):
        DATABASE_URL = raw_db_url.replace("postgres://", "postgresql://", 1)
    else:
        DATABASE_URL = raw_db_url
else:
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Qwen Inference config
HF_TOKEN = os.getenv("HF_TOKEN", "").strip() or None
QWEN_MODEL = os.getenv("QWEN_MODEL", "Qwen/Qwen3.8-27B:novita").strip()
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL", "https://router.huggingface.co/v1").rstrip("/")
