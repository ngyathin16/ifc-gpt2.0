"""SSE status stream and polling endpoint."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from api.deps import get_job

router = APIRouter()


@router.get("/status/{job_id}/stream")
async def stream_status(job_id: str):
    async def generator():
        while True:
            job = get_job(job_id) or {"status": "not_found"}
            yield {"data": json.dumps(job)}
            if job.get("status") in ("complete", "error", "not_found"):
                break
            await asyncio.sleep(1.5)

    return EventSourceResponse(generator())


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    job = get_job(job_id)
    if not job:
        return {"status": "not_found", "job_id": job_id}
    return {"job_id": job_id, **job}
