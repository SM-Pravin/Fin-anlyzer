import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

from src.database.connection import get_database
from src.core.security import hash_password
from src.api.routes_auth import router as auth_router
from src.api.routes_assets import router as assets_router
from src.api.routes_admin import router as admin_router
from src.api.routes_field import router as field_router
from src.api.routes_public import router as public_router

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan: seed default users on first boot
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = await get_database()
    count = await db["users"].count_documents({})
    if count == 0:
        logger.info("No users found – seeding default accounts…")
        default_users = [
            {"username": "admin", "password_hash": hash_password("password"), "role": "admin"},
            {"username": "agent", "password_hash": hash_password("password"), "role": "agent"},
            {"username": "user",  "password_hash": hash_password("password"), "role": "user"},
        ]
        await db["users"].insert_many(default_users)
        logger.info("Default users created: admin / agent / user  (password: 'password')")
    else:
        logger.info("Users collection already populated – skipping seed.")

    # Ensure uploads directory exists
    os.makedirs("uploads", exist_ok=True)

    yield  # application runs here


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="VaultVerify – Enterprise Collateral Verification",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files & uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/static",  StaticFiles(directory="static"),  name="static")

# API routers
app.include_router(auth_router,   prefix="/api/auth",      tags=["Auth"])
app.include_router(assets_router, prefix="/api/assets",    tags=["Assets"])
app.include_router(admin_router,  prefix="/api/admin",     tags=["Admin"])
app.include_router(field_router,  prefix="/api/field",     tags=["Field Agent"])
app.include_router(public_router, prefix="/api/certified", tags=["Public"])


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/static/index.html")
