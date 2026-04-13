"""Tests for building_blocks/primitives/opening.py — fallback branches."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

from building_blocks.primitives.opening import (
    _wall_direction,
    _wall_origin,
    create_opening_in_wall,
    fill_opening,
)
from building_blocks.primitives.wall import create_wall


def test_wall_direction_fallback_on_error():
    """Cover _wall_direction except branch (lines 35-37): when placement read fails."""
    mock_wall = MagicMock()
    mock_wall.ObjectPlacement = None
    with patch(
        "building_blocks.primitives.opening.ifcopenshell.util.placement.get_local_placement",
        side_effect=Exception("bad placement"),
    ):
        direction, angle = _wall_direction(mock_wall)
    assert abs(direction[0] - 1.0) < 1e-6
    assert abs(direction[1] - 0.0) < 1e-6


def test_wall_origin_fallback_on_error():
    """Cover _wall_origin except branch (lines 49-50): when placement read fails."""
    mock_wall = MagicMock()
    mock_wall.ObjectPlacement = None
    with patch(
        "building_blocks.primitives.opening.ifcopenshell.util.placement.get_local_placement",
        side_effect=Exception("bad placement"),
    ):
        origin = _wall_origin(mock_wall)
    assert abs(origin[0]) < 1e-6
    assert abs(origin[1]) < 1e-6
    assert abs(origin[2]) < 1e-6


def test_wall_direction_zero_length_vector():
    """Cover _wall_direction branch where direction length < 1e-6 (lines 33-35)."""
    import numpy as np

    mock_wall = MagicMock()
    # Return a matrix with zero-length X-axis column
    zero_mat = np.eye(4)
    zero_mat[0][0] = 0.0
    zero_mat[1][0] = 0.0
    with patch(
        "building_blocks.primitives.opening.ifcopenshell.util.placement.get_local_placement",
        return_value=zero_mat,
    ):
        direction, angle = _wall_direction(mock_wall)
    assert abs(direction[0] - 1.0) < 1e-6
    assert abs(direction[1] - 0.0) < 1e-6


def test_create_opening_and_fill(ifc_setup):
    """Verify opening creation and fill_opening relationship."""
    ifc, contexts, storey = ifc_setup
    wall = create_wall(
        ifc, contexts, storey,
        p1=(0.0, 0.0), p2=(8.0, 0.0),
        height=3.0, thickness=0.2,
    )
    opening = create_opening_in_wall(
        ifc, contexts, wall,
        distance_along_wall=4.0,
        sill_height=0.9,
        width=1.2,
        height=1.5,
    )
    assert opening is not None
    assert opening.is_a("IfcOpeningElement")

    # Create a dummy window to fill
    import ifcopenshell.api.root
    win = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcWindow", name="W")
    fill_opening(ifc, opening, win)

    fills = ifc.by_type("IfcRelFillsElement")
    assert len(fills) == 1
    assert fills[0].RelatingOpeningElement == opening
    assert fills[0].RelatedBuildingElement == win
