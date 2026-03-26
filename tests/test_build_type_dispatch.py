"""Tests for type dispatch in the build node."""
from __future__ import annotations

from agent.nodes.build import _create_type


def test_dispatch_wall_type_by_preset():
    from building_blocks.context import create_ifc_project
    ifc, _ = create_ifc_project()
    result = _create_type(ifc, "IfcWallType", "exterior_wall", {})
    assert result is not None
    assert result.is_a("IfcWallType")


def test_dispatch_wall_type_by_class_default():
    from building_blocks.context import create_ifc_project
    ifc, _ = create_ifc_project()
    result = _create_type(ifc, "IfcWallType", None, {})
    assert result is not None
    assert result.is_a("IfcWallType")


def test_dispatch_interior_wall_type():
    from building_blocks.context import create_ifc_project
    ifc, _ = create_ifc_project()
    result = _create_type(ifc, "IfcWallType", "interior_wall", {})
    assert result is not None
    assert result.is_a("IfcWallType")


def test_dispatch_column_type_by_preset():
    from building_blocks.context import create_ifc_project
    ifc, _ = create_ifc_project()
    result = _create_type(ifc, "IfcColumnType", "concrete_column", {})
    assert result is not None
    assert result.is_a("IfcColumnType")


def test_dispatch_circular_column_type():
    from building_blocks.context import create_ifc_project
    ifc, _ = create_ifc_project()
    result = _create_type(ifc, "IfcColumnType", "circular_column", {})
    assert result is not None
    assert result.is_a("IfcColumnType")


def test_dispatch_beam_type_concrete():
    from building_blocks.context import create_ifc_project
    ifc, _ = create_ifc_project()
    result = _create_type(ifc, "IfcBeamType", "concrete_beam", {})
    assert result is not None
    assert result.is_a("IfcBeamType")


def test_dispatch_beam_type_steel():
    from building_blocks.context import create_ifc_project
    ifc, _ = create_ifc_project()
    result = _create_type(ifc, "IfcBeamType", "steel_beam", {})
    assert result is not None
    assert result.is_a("IfcBeamType")


def test_dispatch_door_type():
    from building_blocks.context import create_ifc_project
    ifc, _ = create_ifc_project()
    result = _create_type(ifc, "IfcDoorType", "single_swing_door", {})
    assert result is not None
    assert result.is_a("IfcDoorType")


def test_dispatch_fire_door_type():
    from building_blocks.context import create_ifc_project
    ifc, _ = create_ifc_project()
    result = _create_type(ifc, "IfcDoorType", "fire_door", {})
    assert result is not None
    assert result.is_a("IfcDoorType")


def test_dispatch_window_type():
    from building_blocks.context import create_ifc_project
    ifc, _ = create_ifc_project()
    result = _create_type(ifc, "IfcWindowType", "standard_window", {})
    assert result is not None
    assert result.is_a("IfcWindowType")


def test_dispatch_double_glazed_window():
    from building_blocks.context import create_ifc_project
    ifc, _ = create_ifc_project()
    result = _create_type(ifc, "IfcWindowType", "double_glazed_window", {})
    assert result is not None
    assert result.is_a("IfcWindowType")


def test_dispatch_unknown_preset_falls_back_to_class():
    from building_blocks.context import create_ifc_project
    ifc, _ = create_ifc_project()
    result = _create_type(ifc, "IfcWallType", "nonexistent_preset", {})
    assert result is not None
    assert result.is_a("IfcWallType")


def test_dispatch_unknown_class_returns_none():
    from building_blocks.context import create_ifc_project
    ifc, _ = create_ifc_project()
    result = _create_type(ifc, "IfcUnknownType", None, {})
    assert result is None


def test_dispatch_with_custom_params():
    from building_blocks.context import create_ifc_project
    ifc, _ = create_ifc_project()
    result = _create_type(ifc, "IfcWallType", "exterior_wall", {"name": "CUSTOM-WALL-300"})
    assert result is not None
    assert result.is_a("IfcWallType")
    assert result.Name == "CUSTOM-WALL-300"
