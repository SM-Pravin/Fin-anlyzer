import uuid
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import require_role
from src.database.connection import get_database
from src.models.db_models import AssetStatus, AssetType
from src.models.schemas import GoldCertifyInput, LandCertifyInput, MessageResponse

router = APIRouter()


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("/queue")
async def get_field_queue(current_user: dict = Depends(require_role("agent"))):
    """Return all assets with status PHYSICAL_PENDING."""
    db = await get_database()
    cursor = db["assets"].find({"status": AssetStatus.PHYSICAL_PENDING})
    assets = []
    async for doc in cursor:
        assets.append(_serialize(doc))
    return assets


@router.put("/certify/gold/{asset_id}", response_model=MessageResponse)
async def certify_gold(
    asset_id: str,
    body: GoldCertifyInput,
    current_user: dict = Depends(require_role("agent")),
):
    """
    Record physical gold measurements and mark the asset as CERTIFIED.
    Generates a unique certificate_id (UUID).
    """
    if not ObjectId.is_valid(asset_id):
        raise HTTPException(status_code=400, detail="Invalid asset ID format.")

    db = await get_database()
    now = datetime.now(tz=timezone.utc)
    cert_id = str(uuid.uuid4())

    result = await db["assets"].update_one(
        {
            "_id": ObjectId(asset_id),
            "status": AssetStatus.PHYSICAL_PENDING,
            "asset_type": AssetType.GOLD,
        },
        {
            "$set": {
                "status":          AssetStatus.CERTIFIED,
                "measured_weight": body.measured_weight,
                "tested_purity":   body.tested_purity,
                "certificate_id":  cert_id,
                "certified_on":    now,
                "certified_by":    current_user["sub"],
            }
        },
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found, not a gold asset, or not in PHYSICAL_PENDING status.",
        )

    return MessageResponse(message=f"Gold asset certified. Certificate ID: {cert_id}")


@router.put("/certify/land/{asset_id}", response_model=MessageResponse)
async def certify_land(
    asset_id: str,
    body: LandCertifyInput,
    current_user: dict = Depends(require_role("agent")),
):
    """
    Record verified GPS coordinates and mark the asset as CERTIFIED.
    Generates a unique certificate_id (UUID).
    """
    if not ObjectId.is_valid(asset_id):
        raise HTTPException(status_code=400, detail="Invalid asset ID format.")

    db = await get_database()
    now = datetime.now(tz=timezone.utc)
    cert_id = str(uuid.uuid4())

    result = await db["assets"].update_one(
        {
            "_id": ObjectId(asset_id),
            "status": AssetStatus.PHYSICAL_PENDING,
            "asset_type": AssetType.LAND,
        },
        {
            "$set": {
                "status":           AssetStatus.CERTIFIED,
                "gps_lat":          body.verified_gps_lat,
                "gps_long":         body.verified_gps_long,
                "certificate_id":   cert_id,
                "certified_on":     now,
                "certified_by":     current_user["sub"],
            }
        },
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found, not a land asset, or not in PHYSICAL_PENDING status.",
        )

    return MessageResponse(message=f"Land asset certified. Certificate ID: {cert_id}")
