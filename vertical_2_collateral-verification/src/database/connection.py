import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from dotenv import load_dotenv
 
load_dotenv()
 
MONGO_URI     = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "vaultverify")
 
_client: Optional[AsyncIOMotorClient] = None
 
 
async def get_database() -> AsyncIOMotorDatabase:
    """
    Return the singleton Motor database handle.
    Creates the client on first call.
    """
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGO_URI)
    return _client[MONGO_DB_NAME]