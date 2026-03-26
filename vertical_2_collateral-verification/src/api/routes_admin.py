from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import require_role
from src.database.connection import get_database
from src.models.db_models import AssetStatus
from src.models.schemas import MessageResponse

router = APIRouter()


def _serialize(doc: dict) -> dict:
    """Convert ObjectId to str so the document is JSON-serialisable."""
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("/queue")
async def get_admin_queue(current_user: dict = Depends(require_role("admin"))):
    """Return all assets with status DIGITAL_PENDING."""
    db = await get_database()
    cursor = db["assets"].find({"status": AssetStatus.DIGITAL_PENDING})
    assets = []
    async for doc in cursor:
        assets.append(_serialize(doc))
    return assets


@router.put("/approve/{asset_id}", response_model=MessageResponse)
async def approve_asset(
    asset_id: str,
    current_user: dict = Depends(require_role("admin")),
):
    """Move an asset from DIGITAL_PENDING → PHYSICAL_PENDING."""
    if not ObjectId.is_valid(asset_id):
        raise HTTPException(status_code=400, detail="Invalid asset ID format.")

    db = await get_database()
    result = await db["assets"].update_one(
        {"_id": ObjectId(asset_id), "status": AssetStatus.DIGITAL_PENDING},
        {"$set": {"status": AssetStatus.PHYSICAL_PENDING}},
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found or is not in DIGITAL_PENDING status.",
        )

    return MessageResponse(message="Asset approved and forwarded to field agent queue.")


@router.put("/reject/{asset_id}", response_model=MessageResponse)
async def reject_asset(
    asset_id: str,
    current_user: dict = Depends(require_role("admin")),
):
    """Reject a digital-pending asset."""
    if not ObjectId.is_valid(asset_id):
        raise HTTPException(status_code=400, detail="Invalid asset ID format.")

    db = await get_database()
    result = await db["assets"].update_one(
        {"_id": ObjectId(asset_id), "status": AssetStatus.DIGITAL_PENDING},
        {"$set": {"status": AssetStatus.REJECTED}},
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found or is not in DIGITAL_PENDING status.",
        )

    return MessageResponse(message="Asset rejected.")
