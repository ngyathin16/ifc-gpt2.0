"""POST /api/generate — text prompt to IFC generation."""
from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import set_job, update_job, verify_token

logger = logging.getLogger(__name__)

router = APIRouter()


class GenerateRequest(BaseModel):
    message: str
    selected_features: list[str] | None = None
    floor_to_floor_height: float | None = None


@router.post("/generate")
async def generate(req: GenerateRequest, user_id: str | None = Depends(verify_token)):
    job_id = str(uuid.uuid4())[:8]
    set_job(job_id, {"status": "queued", "ifc_url": None, "error": None})
    asyncio.create_task(_run(job_id, req.message, req.selected_features, req.floor_to_floor_height))
    return {"job_id": job_id, "status": "queued"}


async def _run(job_id: str, message: str, selected_features: list[str] | None = None, floor_to_floor_height: float | None = None):
    update_job(job_id, {"status": "running"})
    try:
        from agent.graph import run_pipeline

        loop = asyncio.get_running_loop()
        state = await loop.run_in_executor(
            None, lambda: run_pipeline(message, selected_features=selected_features, floor_to_floor_height=floor_to_floor_height)
        )
        ifc_path = state.get("final_ifc_path", "")
        ifc_url = f"/workspace/{Path(ifc_path).name}" if ifc_path and Path(ifc_path).exists() else None
        update_job(job_id, {"status": "complete", "ifc_url": ifc_url, "error": None})
    except Exception as e:
        logger.exception("Generation failed for job %s", job_id)
        update_job(job_id, {"status": "error", "ifc_url": None, "error": str(e)})
