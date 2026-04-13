"""Tests for agent/nodes/build.py — dispatch table, unique keys, error handling."""
from __future__ import annotations

import logging


from agent.nodes.build import build, _ELEMENT_HANDLERS
from agent.schemas import (
    BuildingPlan,
    OpeningPlacement,
    SlabPlacement,
    StoreyDefinition,
    WallPlacement,
)


def _minimal_plan(**overrides) -> BuildingPlan:
    """Create a minimal valid BuildingPlan for testing."""
    defaults = {
        "description": "Test building",
        "storeys": [StoreyDefinition(storey_ref="F00", name="Ground", elevation=0.0)],
        "elements": [],
    }
    defaults.update(overrides)
    return BuildingPlan(**defaults)


class TestElementHandlers:
    """Verify the dispatch table covers all element types."""

    def test_dispatch_table_has_wall(self):
        assert "wall" in _ELEMENT_HANDLERS

    def test_dispatch_table_has_column(self):
        assert "column" in _ELEMENT_HANDLERS

    def test_dispatch_table_has_beam(self):
        assert "beam" in _ELEMENT_HANDLERS

    def test_dispatch_table_has_slab(self):
        assert "slab" in _ELEMENT_HANDLERS

    def test_dispatch_table_has_door(self):
        assert "door" in _ELEMENT_HANDLERS

    def test_dispatch_table_has_window(self):
        assert "window" in _ELEMENT_HANDLERS

    def test_dispatch_table_has_roof(self):
        assert "roof" in _ELEMENT_HANDLERS

    def test_dispatch_table_has_stair(self):
        assert "stair" in _ELEMENT_HANDLERS

    def test_dispatch_table_has_railing(self):
        assert "railing" in _ELEMENT_HANDLERS

    def test_dispatch_table_has_elevator(self):
        assert "elevator" in _ELEMENT_HANDLERS

    def test_dispatch_table_has_covering(self):
        assert "covering" in _ELEMENT_HANDLERS

    def test_dispatch_table_has_footing(self):
        assert "footing" in _ELEMENT_HANDLERS

    def test_dispatch_table_has_ramp(self):
        assert "ramp" in _ELEMENT_HANDLERS

    def test_dispatch_table_has_balcony(self):
        assert "balcony" in _ELEMENT_HANDLERS


class TestBuildUniqueKeys:
    """Entity keys should never collide, even with multiple elements of the same type."""

    def test_multiple_doors_on_same_wall_unique_keys(self):
        plan = _minimal_plan(
            elements=[
                WallPlacement(
                    wall_ref="W1_F00", storey_ref="F00",
                    start_point=[0, 0], end_point=[10, 0],
                    height=3.0, thickness=0.2,
                ),
                OpeningPlacement(
                    element_type="door", storey_ref="F00",
                    host_wall_ref="W1_F00", distance_along_wall=2.0,
                    width=0.9, height=2.1,
                ),
                OpeningPlacement(
                    element_type="door", storey_ref="F00",
                    host_wall_ref="W1_F00", distance_along_wall=6.0,
                    width=0.9, height=2.1,
                ),
            ],
        )
        state = {"building_plan": plan}
        result = build(state)
        entities = result["ifc_entities"]
        # Both doors should be present (unique keys)
        door_keys = [k for k in entities if k.startswith("door_")]
        assert len(door_keys) == 2
        assert door_keys[0] != door_keys[1]

    def test_multiple_slabs_unique_keys(self):
        plan = _minimal_plan(
            elements=[
                SlabPlacement(
                    storey_ref="F00",
                    boundary_points=[[0, 0], [10, 0], [10, 10], [0, 10]],
                    depth=0.2,
                ),
                SlabPlacement(
                    storey_ref="F00",
                    boundary_points=[[10, 0], [20, 0], [20, 10], [10, 10]],
                    depth=0.2,
                ),
            ],
        )
        state = {"building_plan": plan}
        result = build(state)
        entities = result["ifc_entities"]
        slab_keys = [k for k in entities if k.startswith("slab_")]
        assert len(slab_keys) == 2


class TestBuildMissingRefs:
    """Missing storey_ref or host_wall_ref should log warnings, not silently skip."""

    def test_missing_storey_ref_warns(self, caplog):
        plan = _minimal_plan(
            elements=[
                WallPlacement(
                    wall_ref="W1_F99", storey_ref="F99",
                    start_point=[0, 0], end_point=[10, 0],
                ),
            ],
        )
        state = {"building_plan": plan}
        with caplog.at_level(logging.WARNING):
            result = build(state)
        assert any("F99" in msg for msg in caplog.messages)

    def test_missing_host_wall_warns(self, caplog):
        plan = _minimal_plan(
            elements=[
                OpeningPlacement(
                    element_type="door", storey_ref="F00",
                    host_wall_ref="W_NONEXISTENT", distance_along_wall=1.0,
                    width=0.9, height=2.1,
                ),
            ],
        )
        state = {"building_plan": plan}
        with caplog.at_level(logging.WARNING):
            result = build(state)
        assert any("W_NONEXISTENT" in msg for msg in caplog.messages)
