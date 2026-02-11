from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from supabase import create_client

from app.core.config import get_settings


def _get_client():
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase storage is not configured",
        )
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def upload_user_photo(file: UploadFile, user_id: int) -> str:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file",
        )

    settings = get_settings()
    if not settings.supabase_storage_bucket:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase storage bucket is not configured",
        )

    file_bytes = file.file.read()
    extension = ""
    if file.content_type and "/" in file.content_type:
        extension = f".{file.content_type.split('/')[-1]}"
    path = f"profile_pictures/{user_id}/avatar{extension}"

    client = _get_client()
    storage = client.storage.from_(settings.supabase_storage_bucket)
    storage.upload(
        path,
        file_bytes,
        {
            "content-type": file.content_type or "application/octet-stream",
            "x-upsert": "true",
        },
    )

    public_url = storage.get_public_url(path)
    if not public_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate public URL",
        )

    return public_url


def upload_calibration_certificate(file: UploadFile, calibration_id: int) -> str:
    content_type = (file.content_type or "").lower()
    filename = (file.filename or "").lower()
    if content_type != "application/pdf" and not filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid PDF file",
        )

    settings = get_settings()
    if not settings.supabase_storage_bucket:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase storage bucket is not configured",
        )

    file_bytes = file.file.read()
    path = f"calibration_certificates/{calibration_id}/certificate.pdf"

    client = _get_client()
    storage = client.storage.from_(settings.supabase_storage_bucket)
    storage.upload(
        path,
        file_bytes,
        {
            "content-type": "application/pdf",
            "x-upsert": "true",
        },
    )
    public_url = storage.get_public_url(path)
    if not public_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate public URL",
        )
    return public_url


def delete_user_photo(photo_url: str) -> None:
    if not photo_url:
        return

    settings = get_settings()
    if not settings.supabase_storage_bucket:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase storage bucket is not configured",
        )

    base = settings.supabase_url or ""
    prefix = f"{base}/storage/v1/object/public/{settings.supabase_storage_bucket}/"
    if photo_url.startswith(prefix):
        path = photo_url.replace(prefix, "")
    else:
        path = photo_url.split(f"/{settings.supabase_storage_bucket}/")[-1]

    client = _get_client()
    storage = client.storage.from_(settings.supabase_storage_bucket)
    storage.remove([path])
