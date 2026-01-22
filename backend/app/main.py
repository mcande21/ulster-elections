"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .routers import races, upload
from .services.database import init_pool, close_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup and shutdown)."""
    # Startup
    init_pool()
    yield
    # Shutdown
    close_pool()


app = FastAPI(
    title="Ulster Elections API",
    description="API for 2025 Ulster County election results",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(races.router)
app.include_router(upload.router)


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "Ulster Elections API",
        "version": "1.0.0",
        "endpoints": {
            "races": "/api/races",
            "stats": "/api/stats",
            "filters": "/api/filters",
            "upload": "/api/upload"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
