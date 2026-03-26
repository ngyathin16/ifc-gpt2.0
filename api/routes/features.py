"""GET /api/features — return available building features for the frontend menu."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from agent.nodes.clarify import BUILDING_FEATURES, _infer_defaults

router = APIRouter()


class FeatureItem(BaseModel):
    id: str
    category: str
    label: str
    description: str
    default_for: list[str]


class InferRequest(BaseModel):
    message: str


class InferResponse(BaseModel):
    building_type: str
    num_storeys: int
    floor_to_floor_height: float
    default_features: list[str]


@router.get("/features")
async def get_features() -> list[FeatureItem]:
    """Return the full catalogue of building features grouped by category."""
    return [FeatureItem(**f) for f in BUILDING_FEATURES]


@router.post("/features/infer")
async def infer_features(req: InferRequest) -> InferResponse:
    """Given a user prompt, infer building type and default features."""
    defaults = _infer_defaults(req.message)
    return InferResponse(**defaults)
