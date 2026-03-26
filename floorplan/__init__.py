"""
FloorPlan2IFC — convert 2D floor plan images to IFC BuildingPlan JSON.

Pipeline:
    ingest → scale → detect → vectorise → plan_builder
"""
from __future__ import annotations
