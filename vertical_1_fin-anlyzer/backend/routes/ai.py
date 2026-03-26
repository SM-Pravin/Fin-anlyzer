"""
AI routes: context-aware chat and multimodal document analysis (HITL).
"""

import os
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.encoders import jsonable_encoder
from fastapi.responses import PlainTextResponse

from backend.database import get_db
from backend.models import ChatRequest
from backend.services.llm_service import chat_with_context, analyze_document_with_llm
from backend.services.document_parser import parse_document_to_base64

router = APIRouter()

# Resolve system_prompt.txt relative to project root (two levels up from this file)
_PROMPT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "system_prompt.txt",
)


@router.get("/system_prompt", response_class=PlainTextResponse)
async def get_system_prompt():
    """Returns the contents of system_prompt.txt for the frontend toggle."""
    try:
        with open(_PROMPT_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not read system_prompt.txt: {exc}")

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Fetches live DB state, injects it as system context,
    then forwards the user message to the local Qwen3-VL endpoint.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    db = get_db()

    # Pull current financial state — capped at 50 to stay within context window
    assets      = await db.assets.find().to_list(50)
    payables    = await db.payables.find({"status": "Pending"}).to_list(50)
    receivables = await db.receivables.find({"status": "Pending"}).to_list(50)

    # Strip MongoDB internals before serialising
    for doc in assets + payables + receivables:
        doc.pop("_id", None)

    context = {
        "assets":      jsonable_encoder(assets),
        "payables":    jsonable_encoder(payables),
        "receivables": jsonable_encoder(receivables),
    }

    try:
        response_text = await chat_with_context(
            request.message, context, request.custom_instruction
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"LLM service unavailable: {exc}",
        )

    return {"response": response_text}


@router.post("/analyze_document")
async def analyze_document(file: UploadFile = File(...)):
    """
    HUMAN-IN-THE-LOOP constraint:
      Converts the uploaded PDF/image → base64 images → sends to VLM for
      structured JSON extraction, then returns the result to the frontend
      for human review.  Nothing is saved to MongoDB here.
    """
    filename = (file.filename or "upload").lower()
    if not any(filename.endswith(ext) for ext in (".pdf", ".png", ".jpg", ".jpeg", ".webp")):
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Please upload a PDF or image (PNG/JPG/WEBP).",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")

    try:
        images_b64 = await parse_document_to_base64(content, filename)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Document parsing failed: {exc}")

    if not images_b64:
        raise HTTPException(status_code=422, detail="Could not extract any images from the document")

    try:
        extracted = await analyze_document_with_llm(images_b64)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"LLM analysis failed: {exc}")

    # ⚠️  HITL: return to client for review — never auto-save
    return {
        "extracted_data": extracted,
        "message": "Review the extracted data carefully before confirming.",
        "pages_analysed": len(images_b64),
    }