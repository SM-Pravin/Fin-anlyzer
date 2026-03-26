"""
Document parser: converts uploaded PDF or image → list of base64 PNG strings.
Each string represents one page, ready to be sent to a Vision-Language Model.
"""

import base64
from io import BytesIO


async def parse_document_to_base64(content: bytes, filename: str) -> list[str]:
    """
    Parameters
    ----------
    content  : raw file bytes
    filename : original filename (used to detect type)

    Returns
    -------
    List of base64-encoded PNG strings (one per page / image).
    """
    images_b64: list[str] = []

    if filename.endswith(".pdf"):
        # pdf2image requires poppler to be installed on the system
        # Install: sudo apt-get install poppler-utils  (Debian/Ubuntu)
        #          brew install poppler                 (macOS)
        from pdf2image import convert_from_bytes

        images = convert_from_bytes(
            content,
            dpi=150,       # Balanced: readable by VLM, not too large
            fmt="PNG",
            thread_count=2,
        )
        for img in images:
            buf = BytesIO()
            img.save(buf, format="PNG", optimize=True)
            images_b64.append(base64.b64encode(buf.getvalue()).decode("utf-8"))

    elif filename.endswith((".png", ".jpg", ".jpeg", ".webp")):
        # For images, normalise to PNG via Pillow for consistency
        from PIL import Image

        img = Image.open(BytesIO(content)).convert("RGB")
        buf = BytesIO()
        img.save(buf, format="PNG", optimize=True)
        images_b64.append(base64.b64encode(buf.getvalue()).decode("utf-8"))

    else:
        raise ValueError(f"Unsupported file extension in: {filename}")

    return images_b64