"""POST /api/voice — audio file to Whisper transcription to IFC generation."""
from __future__ import annotations

import asyncio
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from openai import OpenAI

from api.deps import set_job, update_job, verify_token

router = APIRouter()


@router.post("/voice")
async def voice(audio: UploadFile, user_id: str | None = Depends(verify_token)):
    job_id = str(uuid.uuid4())[:8]
    set_job(job_id, {"status": "queued", "ifc_url": None, "error": None, "transcript": None})
    asyncio.create_task(_run(job_id, audio))
    return {"job_id": job_id, "status": "queued"}


async def _run(job_id: str, audio: UploadFile):
    update_job(job_id, {"status": "transcribing"})
    try:
        # Write audio to temp file
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Transcribe with Whisper
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        with open(tmp_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
            )
        transcript = transcription.text

        # Clean up temp file
        Path(tmp_path).unlink(missing_ok=True)

        update_job(job_id, {"status": "running", "transcript": transcript})

        # Run the generation pipeline with the transcript
        from agent.graph import run_pipeline

        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(None, lambda: run_pipeline(transcript))
        ifc_path = state.get("final_ifc_path", "")
        ifc_url = f"/workspace/{Path(ifc_path).name}" if ifc_path and Path(ifc_path).exists() else None
        update_job(job_id, {"status": "complete", "ifc_url": ifc_url, "error": None})
    except Exception as e:
        update_job(job_id, {"status": "error", "ifc_url": None, "error": str(e)})
