"""POST /api/modify — GUID-targeted modification of an existing IFC."""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import set_job, update_job, verify_token

router = APIRouter()


class ModifyRequest(BaseModel):
    guid: str
    instruction: str
    ifc_url: str  # path to the current IFC file


@router.post("/modify")
async def modify(req: ModifyRequest, user_id: str | None = Depends(verify_token)):
    job_id = str(uuid.uuid4())[:8]
    set_job(job_id, {"status": "queued", "ifc_url": None, "error": None})
    asyncio.create_task(_run(job_id, req.guid, req.instruction, req.ifc_url))
    return {"job_id": job_id, "status": "queued"}


async def _run(job_id: str, guid: str, instruction: str, ifc_url: str):
    update_job(job_id, {"status": "running"})
    try:
        from agent.graph import run_modify_pipeline

        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(
            None, lambda: run_modify_pipeline(guid, instruction, ifc_url)
        )
        ifc_path = state.get("final_ifc_path", "")
        new_ifc_url = f"/workspace/{Path(ifc_path).name}" if ifc_path and Path(ifc_path).exists() else None
        update_job(job_id, {"status": "complete", "ifc_url": new_ifc_url, "error": None})
    except Exception as e:
        update_job(job_id, {"status": "error", "ifc_url": None, "error": str(e)})
