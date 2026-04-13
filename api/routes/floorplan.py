"""
FloorPlan2IFC API routes.

POST /api/floorplan/upload — upload a floor plan image/PDF, run detection
GET  /api/floorplan/{job_id}/plan — get detected plan for review
POST /api/floorplan/{job_id}/confirm — confirm plan and trigger IFC build

State machine (GUARDRAIL G-24):
  detecting -> awaiting_confirmation -> building -> complete
                     |                       |
                   error                   error
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from api.deps import get_job, set_job, update_job, verify_token

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}
MAX_PDF_BYTES = 50 * 1024 * 1024   # 50 MB (GUARDRAIL G-01)
MAX_IMG_BYTES = 25 * 1024 * 1024   # 25 MB (GUARDRAIL G-01)


@router.post("/floorplan/upload")
async def upload_floorplan(
    file: UploadFile = File(...),
    num_storeys: int = Form(1),
    floor_to_floor_height: float = Form(3.0),
    detection_backend: str = Form("opencv"),
    user_id: str | None = Depends(verify_token),
):
    """Accept a floor plan image/PDF upload and run detection.

    Returns a job_id. Detection runs asynchronously.
    After detection completes, job status moves to 'awaiting_confirmation'
    and the detected plan can be reviewed via GET /api/floorplan/{job_id}/plan.
    """
    filename = file.filename or "plan.png"
    suffix = Path(filename).suffix.lower()

    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(400, "Unsupported file type. Accepted: PDF, PNG, JPEG, TIFF.")

    file_bytes = await file.read()

    # File size validation (GUARDRAIL G-01)
    max_bytes = MAX_PDF_BYTES if suffix == ".pdf" else MAX_IMG_BYTES
    if len(file_bytes) > max_bytes:
        raise HTTPException(400, f"File too large. Max: {max_bytes // (1024*1024)} MB.")

    job_id = uuid.uuid4().hex[:8]
    set_job(job_id, {
        "status": "detecting",
        "ifc_url": None,
        "plan_json": None,
        "scale": None,
        "error": None,
        "floorplan_metadata": None,
    })

    asyncio.create_task(_run_detection(
        job_id, file_bytes, filename, num_storeys, floor_to_floor_height,
        detection_backend,
    ))
    return {"job_id": job_id, "status": "detecting"}


@router.get("/floorplan/{job_id}/plan")
async def get_plan(job_id: str):
    """Get the detected BuildingPlan JSON for review before confirming."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    status = job.get("status")
    if status == "detecting":
        return {"job_id": job_id, "status": "detecting", "plan": None}
    if status == "error":
        return {"job_id": job_id, "status": "error", "error": job.get("error")}
    return {
        "job_id": job_id,
        "status": status,
        "plan": job.get("plan_json"),
        "scale": job.get("scale"),
        "metadata": job.get("floorplan_metadata"),
    }


class ConfirmPayload(BaseModel):
    plan: dict


@router.post("/floorplan/{job_id}/confirm")
async def confirm_plan(job_id: str, payload: ConfirmPayload):
    """Confirm the detected plan (optionally edited) and trigger IFC build."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.get("status") not in ("awaiting_confirmation", "complete"):
        raise HTTPException(409, f"Job not ready for confirmation: {job.get('status')}")

    update_job(job_id, {"status": "building", "plan_json": payload.plan})
    asyncio.create_task(_run_build(job_id, payload.plan))
    return {"job_id": job_id, "status": "building"}


# Legacy endpoint — kept for backwards compatibility
@router.post("/floorplan")
async def upload_floorplan_legacy(
    file: UploadFile = File(...),
    num_storeys: int = Form(1),
    floor_to_floor_height: float = Form(3.0),
    user_id: str | None = Depends(verify_token),
):
    """Legacy endpoint: upload + auto-build without confirmation step."""
    job_id = uuid.uuid4().hex[:8]
    set_job(job_id, {"status": "detecting", "ifc_url": None, "error": None})

    file_bytes = await file.read()
    filename = file.filename or "plan.png"

    asyncio.create_task(_run_legacy(
        job_id, file_bytes, filename, num_storeys, floor_to_floor_height,
    ))
    return {"job_id": job_id, "status": "detecting"}


# ---------------------------------------------------------------------------
# Background tasks (GUARDRAIL G-23: all exceptions caught and logged)
# ---------------------------------------------------------------------------

async def _run_detection(
    job_id: str,
    file_bytes: bytes,
    filename: str,
    num_storeys: int,
    floor_to_floor_height: float,
    detection_backend: str = "opencv",
):
    """Detect elements from floor plan image → BuildingPlan JSON."""
    try:
        from floorplan.pipeline import floorplan_to_plan

        loop = asyncio.get_running_loop()
        plan_dict = await loop.run_in_executor(
            None,
            lambda: floorplan_to_plan(
                file_bytes,
                filename=filename,
                num_storeys=num_storeys,
                floor_to_floor_height=floor_to_floor_height,
                detection_backend=detection_backend,
            ),
        )

        metadata = plan_dict.pop("floorplan_metadata", {})
        scale = metadata.get("scale")

        update_job(job_id, {
            "status": "awaiting_confirmation",
            "plan_json": plan_dict,
            "scale": scale,
            "floorplan_metadata": metadata,
            "error": None,
        })
    except Exception as e:
        logger.exception("Detection failed for job %s", job_id)
        update_job(job_id, {"status": "error", "error": str(e)})


async def _run_build(job_id: str, plan_dict: dict):
    """Build IFC from confirmed plan."""
    try:
        from agent.graph import run_pipeline_from_plan

        loop = asyncio.get_running_loop()
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
        })
    except Exception as e:
        logger.exception("Build failed for job %s", job_id)
        update_job(job_id, {"status": "error", "error": str(e)})


async def _run_legacy(
    job_id: str,
    file_bytes: bytes,
    filename: str,
    num_storeys: int,
    floor_to_floor_height: float,
):
    """Legacy: detect + build without confirmation step."""
    update_job(job_id, {"status": "detecting"})
    try:
        from floorplan.pipeline import floorplan_to_plan

        loop = asyncio.get_running_loop()
        plan_dict = await loop.run_in_executor(
            None,
            lambda: floorplan_to_plan(
                file_bytes,
                filename=filename,
                num_storeys=num_storeys,
                floor_to_floor_height=floor_to_floor_height,
            ),
        )

        metadata = plan_dict.pop("floorplan_metadata", {})
        update_job(job_id, {"status": "building", "floorplan_metadata": metadata})

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
        logger.exception("Legacy floorplan pipeline failed for job %s", job_id)
        update_job(job_id, {"status": "error", "ifc_url": None, "error": str(e)})
