"""
Simple in-memory job store (replace with Supabase jobs table in production).
Also provides Supabase JWT verification dependency.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

_jobs: dict[str, dict[str, Any]] = {}


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def set_job(job_id: str, data: dict):
    _jobs[job_id] = data


def update_job(job_id: str, patch: dict):
    if job_id in _jobs:
        _jobs[job_id].update(patch)


# --- JWT verification (Supabase) ---
security = HTTPBearer(auto_error=False)


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Optional auth: returns user_id if token valid, None otherwise."""
    if credentials is None:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            os.getenv("SUPABASE_JWT_SECRET", ""),
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
