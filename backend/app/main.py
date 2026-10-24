import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routers import health, maintainer, beginner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("contribo.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database cache table
    logger.info("Initializing SQLite cache database...")
    init_db()
    yield
    logger.info("Contrib API shutting down.")

app = FastAPI(
    title="Contrib Evidence Engine API",
    description="Evidence-driven agent for contributor issue discovery and maintainer PR review",
    version="0.1.0",
    lifespan=lifespan
)

# Enable CORS for frontend origin (allowing localhost ports and file:// access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(health.router)
app.include_router(maintainer.router)
app.include_router(beginner.router)

# Mount frontend static files from root directory so entire app can run on one server
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.exists(os.path.join(frontend_dir, "index.html")):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="static_frontend")
