"""
Supabase Storage helper for uploading IFC files.

In production, IFC files are uploaded to Supabase Storage instead of
being served from the local workspace/ directory. Uses signed URLs
for secure access (IFC files may contain sensitive client data).
"""
from __future__ import annotations

import os
from pathlib import Path

_client = None


def _get_supabase():
    """Lazy-init Supabase client using service role key."""
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return None
        from supabase import create_client

        _client = create_client(url, key)
    return _client


def upload_ifc(local_path: str | Path, job_id: str) -> str | None:
    """
    Upload an IFC file to Supabase Storage bucket 'ifc-files'.

    Args:
        local_path: Path to the local IFC file.
        job_id: Job identifier used as the storage key.

    Returns:
        Signed URL for the uploaded file (valid 1 hour), or None if
        Supabase is not configured (falls back to local serving).
    """
    client = _get_supabase()
    if client is None:
        return None

    local_path = Path(local_path)
    if not local_path.exists():
        return None

    storage_path = f"jobs/{job_id}.ifc"

    try:
        bucket = client.storage.from_("ifc-files")
        with open(local_path, "rb") as f:
            bucket.upload(
                storage_path,
                f,
                {"content-type": "application/x-step"},
            )
        signed = bucket.create_signed_url(storage_path, expires_in=3600)
        return signed.get("signedURL") or signed.get("signedUrl")
    except Exception:
        return None
