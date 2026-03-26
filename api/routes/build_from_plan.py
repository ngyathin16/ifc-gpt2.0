"""POST /api/build-from-plan — pascal editor JSON to IFC generation."""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import set_job, update_job, verify_token

router = APIRouter()


class BuildFromPlanRequest(BaseModel):
    plan: dict  # BuildingPlan JSON from the Pascal editor


@router.post("/build-from-plan")
async def build_from_plan(req: BuildFromPlanRequest, user_id: str | None = Depends(verify_token)):
    job_id = str(uuid.uuid4())[:8]
    set_job(job_id, {"status": "queued", "ifc_url": None, "error": None})
    asyncio.create_task(_run(job_id, req.plan))
    return {"job_id": job_id, "status": "queued"}


async def _run(job_id: str, plan: dict):
    update_job(job_id, {"status": "running"})
    try:
        from agent.graph import run_pipeline_from_plan

        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(None, lambda: run_pipeline_from_plan(plan))
        ifc_path = state.get("final_ifc_path", "")
        ifc_url = f"/workspace/{Path(ifc_path).name}" if ifc_path and Path(ifc_path).exists() else None
        update_job(job_id, {"status": "complete", "ifc_url": ifc_url, "error": None})
    except Exception as e:
        update_job(job_id, {"status": "error", "ifc_url": None, "error": str(e)})
