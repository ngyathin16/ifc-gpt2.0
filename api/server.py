"""FastAPI application factory for IFC-GPT v2."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

load_dotenv()

WORKSPACE = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
WORKSPACE.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield  # Add startup / shutdown logic here (e.g., warm up LLM)


app = FastAPI(title="IFC-GPT v2", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/workspace", StaticFiles(directory=str(WORKSPACE)), name="workspace")

# Register routes
from api.routes import generate, build_from_plan, modify, voice, status, features, bsdd, floorplan  # noqa: E402

app.include_router(generate.router, prefix="/api")
app.include_router(build_from_plan.router, prefix="/api")
app.include_router(modify.router, prefix="/api")
app.include_router(voice.router, prefix="/api")
app.include_router(status.router, prefix="/api")
app.include_router(features.router, prefix="/api")
app.include_router(bsdd.router, prefix="/api")
app.include_router(floorplan.router, prefix="/api")


def main():
    import sys

    import uvicorn

    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8000
    uvicorn.run("api.server:app", host="0.0.0.0", port=port, reload=True)
