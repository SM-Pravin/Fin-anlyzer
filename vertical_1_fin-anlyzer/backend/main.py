"""
FastAPI application entry-point.

Run from the project root:
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import connect_db, close_db
from backend.routes.finance import router as finance_router
from backend.routes.ai import router as ai_router
from backend.services.setup_manager import ensure_ollama_ready


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_ollama_ready()
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title="Financial Command Center",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (allow all origins in dev; restrict in production) ──────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API Routers (must be registered BEFORE static files mount) ───────────────
app.include_router(finance_router, prefix="/api", tags=["Finance"])
app.include_router(ai_router, prefix="/api", tags=["AI"])

# ── Serve the SPA (fallback to index.html for all unmatched routes) ──────────
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")