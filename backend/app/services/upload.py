import os
import uuid
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from app.config import settings

ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
}

# Magic bytes signatures for true content verification
MAGIC_BYTES = {
    "application/pdf": [b"%PDF"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/jpg": [b"\xff\xd8\xff"],
}

# Signatures of prohibited executable or binary disguise formats
PROHIBITED_SIGNATURES = [
    b"MZ",          # Windows DOS/PE Executable (.exe, .dll)
    b"\x7fELF",     # Linux ELF executable
    b"\xca\xfe\xba\xbe", # Java class / Mach-O universal binary
    b"PK\x03\x04",  # ZIP/JAR (unless specifically handling archives, here prohibited for PDF/Images)
]

MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

async def save_uploaded_file(file: UploadFile, subfolder: str = "general") -> tuple[str, str, int, str]:
    """
    Validates file MIME type, magic bytes signatures, and size.
    Detects disguised files (e.g. .exe renamed to .pdf).
    Saves file to UPLOAD_DIR and returns (file_name, file_path, file_size, content_type).
    """
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file MIME type '{content_type}'. Allowed types: PDF, PNG, JPG/JPEG.",
        )

    contents = await file.read()
    file_size = len(contents)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    if file_size > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB}MB (received {file_size / (1024*1024):.2f}MB).",
        )

    # Check for prohibited signatures (e.g., .exe renamed as .pdf)
    for sig in PROHIBITED_SIGNATURES:
        if contents.startswith(sig):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: Executable or prohibited binary signature detected in uploaded file payload.",
            )

    # Validate true magic bytes for expected format
    expected_signatures = MAGIC_BYTES.get(content_type, [])
    valid_magic = any(contents.startswith(sig) for sig in expected_signatures)
    if not valid_magic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File content does not match the declared MIME type header '{content_type}'. Fake extension detected.",
        )

    ext = ALLOWED_MIME_TYPES[content_type]
    safe_name = f"{uuid.uuid4().hex}_{Path(file.filename or 'file').stem[:30]}{ext}"
    target_dir = Path(settings.UPLOAD_DIR) / subfolder
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / safe_name

    with open(target_path, "wb") as f:
        f.write(contents)

    return file.filename or safe_name, str(target_path), file_size, content_type
