from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
import io

from src.database.connection import get_database
from src.models.schemas import CertifiedAssetPublicResponse
from src.services.cert_service import generate_certificate_pdf

router = APIRouter()


@router.get("/{cert_id}", response_model=CertifiedAssetPublicResponse)
async def get_certificate(cert_id: str):
    """
    Public endpoint – no authentication required.
    Looks up an asset by its certificate_id string.
    The PAN is automatically masked by the Pydantic validator before
    the response is serialised (first 6 chars → XXXXXX).
    MongoDB _id is never included in the response model.
    """
    db = await get_database()
    doc = await db["assets"].find_one({"certificate_id": cert_id})

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found. Please check the ID and try again.",
        )

    doc.pop("_id", None)
    return CertifiedAssetPublicResponse(**doc)


@router.get("/{cert_id}/pdf")
async def download_certificate_pdf(cert_id: str):
    """
    Public endpoint – no authentication required.
    Streams a professionally formatted PDF certificate for the given cert_id.
    """
    db = await get_database()
    doc = await db["assets"].find_one({"certificate_id": cert_id})

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found. Please check the ID and try again.",
        )

    doc.pop("_id", None)

    # Mask PAN before passing to PDF generator (same rule as JSON endpoint)
    pan = doc.get("pan_number", "")
    if len(pan) > 6:
        doc["pan_number"] = "X" * 6 + pan[6:]
    else:
        doc["pan_number"] = "X" * len(pan)

    pdf_bytes = generate_certificate_pdf(doc)

    filename = f"VaultVerify_Certificate_{cert_id[:8]}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )