"""POST /api/floorplan — upload a floor plan image and convert to IFC."""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel

from api.deps import set_job, update_job, verify_token

router = APIRouter()


@router.post("/floorplan")
async def upload_floorplan(
    file: UploadFile = File(...),
    num_storeys: int = Form(1),
    floor_to_floor_height: float = Form(3.0),
    user_id: str | None = Depends(verify_token),
):
    """Accept a floor plan image/PDF upload and run the FloorPlan2IFC pipeline.

    The file is processed through: ingest → scale → detect → vectorise → plan_builder → build.
    Returns a job_id for SSE status polling.
    """
    job_id = str(uuid.uuid4())[:8]
    set_job(job_id, {"status": "queued", "ifc_url": None, "error": None, "plan": None})

    file_bytes = await file.read()
    filename = file.filename or "plan.png"

    asyncio.create_task(_run(
        job_id, file_bytes, filename, num_storeys, floor_to_floor_height,
    ))
    return {"job_id": job_id, "status": "queued"}


async def _run(
    job_id: str,
    file_bytes: bytes,
    filename: str,
    num_storeys: int,
    floor_to_floor_height: float,
):
    import traceback

    update_job(job_id, {"status": "running", "step": "detecting"})
    try:
        from floorplan.pipeline import floorplan_to_plan

        loop = asyncio.get_event_loop()

        # Step 1: Floor plan → BuildingPlan dict
        plan_dict = await loop.run_in_executor(
            None,
            lambda: floorplan_to_plan(
                file_bytes,
                filename=filename,
                num_storeys=num_storeys,
                floor_to_floor_height=floor_to_floor_height,
            ),
        )

        # Store the plan in the job for frontend preview
        metadata = plan_dict.pop("floorplan_metadata", {})
        update_job(job_id, {
            "status": "running",
            "step": "building",
            "floorplan_metadata": metadata,
        })

        # Step 2: BuildingPlan → IFC file
        from agent.graph import run_pipeline_from_plan

        state = await loop.run_in_executor(
            None, lambda: run_pipeline_from_plan(plan_dict),
        )

        ifc_path = state.get("final_ifc_path", "")
        ifc_url = (
            f"/workspace/{Path(ifc_path).name}"
            if ifc_path and Path(ifc_path).exists()
            else None
        )
        update_job(job_id, {
            "status": "complete",
            "ifc_url": ifc_url,
            "error": None,
            "floorplan_metadata": metadata,
        })
    except Exception as e:
        traceback.print_exc()
        update_job(job_id, {"status": "error", "ifc_url": None, "error": str(e)})
