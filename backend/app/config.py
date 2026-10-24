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
