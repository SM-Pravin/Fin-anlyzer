"""
Motor (async MongoDB) client — initialised once at startup via FastAPI lifespan.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME: str = os.getenv("DATABASE_NAME", "financial_command_center")

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_db() -> None:
    global _client, _db
    _client = AsyncIOMotorClient(MONGO_URI)
    _db = _client[DATABASE_NAME]
    # Create lightweight indexes for fast lookups
    await _db.assets.create_index("id", unique=True)
    await _db.payables.create_index("id", unique=True)
    await _db.receivables.create_index("id", unique=True)
    await _db.transactions.create_index("id", unique=True)
    print(f"✅  Connected to MongoDB › {DATABASE_NAME}")


async def close_db() -> None:
    global _client
    if _client:
        _client.close()
        print("🛑  MongoDB connection closed")


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not initialised — call connect_db() first")
    return _db