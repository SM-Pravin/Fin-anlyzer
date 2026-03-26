from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from src.api.dependencies import require_role
from src.database.connection import get_database
from src.models.db_models import AssetStatus, AssetType
from src.models.schemas import MessageResponse
from src.services.file_service import save_upload_file

router = APIRouter()


# ---------------------------------------------------------------------------
# Gold submission
# ---------------------------------------------------------------------------

@router.post("/gold", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def submit_gold(
    applicant_name:   str   = Form(...),
    pan_number:       str   = Form(...),
    declared_weight:  float = Form(...),
    declared_purity:  str   = Form(...),
    structure:        str   = Form(...),
    files: List[UploadFile] = File(...),
    current_user: dict      = Depends(require_role("user")),
):
    if not applicant_name.strip():
        raise HTTPException(status_code=400, detail="Applicant name is required.")
    if not pan_number.strip():
        raise HTTPException(status_code=400, detail="PAN number is required.")
    if declared_weight <= 0:
        raise HTTPException(status_code=400, detail="Declared weight must be positive.")

    saved_urls = [await save_upload_file(f) for f in files if f.filename]

    doc = {
        "applicant_name":  applicant_name.strip(),
        "pan_number":      pan_number.strip().upper(),
        "asset_type":      AssetType.GOLD,
        "status":          AssetStatus.DIGITAL_PENDING,
        "submitted_at":    datetime.now(tz=timezone.utc),
        "document_urls":   saved_urls,
        "declared_weight": declared_weight,
        "declared_purity": declared_purity.strip(),
        "structure":       structure.strip(),
        "measured_weight": None,
        "tested_purity":   None,
        "certificate_id":  None,
        "certified_on":    None,
        "submitted_by":    current_user["sub"],
    }

    db = await get_database()
    await db["assets"].insert_one(doc)
    return MessageResponse(message="Gold asset submitted successfully. Awaiting digital review.")


# ---------------------------------------------------------------------------
# Land submission
# ---------------------------------------------------------------------------

@router.post("/land", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def submit_land(
    applicant_name:  str   = Form(...),
    pan_number:      str   = Form(...),
    property_address: str  = Form(...),
    gps_lat:         float = Form(...),
    gps_long:        float = Form(...),
    declared_size:   float = Form(...),
    land_use_type:   str   = Form(...),
    files: List[UploadFile] = File(...),
    current_user: dict     = Depends(require_role("user")),
):
    if not applicant_name.strip():
        raise HTTPException(status_code=400, detail="Applicant name is required.")
    if not pan_number.strip():
        raise HTTPException(status_code=400, detail="PAN number is required.")
    if not property_address.strip():
        raise HTTPException(status_code=400, detail="Property address is required.")

    saved_urls = [await save_upload_file(f) for f in files if f.filename]

    doc = {
        "applicant_name":  applicant_name.strip(),
        "pan_number":      pan_number.strip().upper(),
        "asset_type":      AssetType.LAND,
        "status":          AssetStatus.DIGITAL_PENDING,
        "submitted_at":    datetime.now(tz=timezone.utc),
        "document_urls":   saved_urls,
        "property_address": property_address.strip(),
        "gps_lat":         gps_lat,
        "gps_long":        gps_long,
        "declared_size":   declared_size,
        "land_use_type":   land_use_type.strip(),
        "certificate_id":  None,
        "certified_on":    None,
        "submitted_by":    current_user["sub"],
    }

    db = await get_database()
    await db["assets"].insert_one(doc)
    return MessageResponse(message="Land asset submitted successfully. Awaiting digital review.")
