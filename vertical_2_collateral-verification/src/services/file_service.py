import os
import uuid
from fastapi import UploadFile

UPLOAD_DIR = "uploads"


async def save_upload_file(file: UploadFile) -> str:
    """
    Saves a FastAPI UploadFile to the local /uploads directory.
    Returns the relative URL path, e.g. '/uploads/abc123_doc.pdf'.
    """
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Ensure a unique filename to prevent collisions
    ext = os.path.splitext(file.filename or "file")[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path   = os.path.join(UPLOAD_DIR, unique_name)

    contents = await file.read()
    with open(dest_path, "wb") as f:
        f.write(contents)

    # Return a URL-style relative path
    return f"/{UPLOAD_DIR}/{unique_name}"
