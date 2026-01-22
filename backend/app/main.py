"""FastAPI application entry point."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import races, upload


app = FastAPI(
    title="Ulster Elections API",
    description="API for 2025 Ulster County election results",
    version="1.0.0"
)

# CORS configuration - supports environment variable for production
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

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
