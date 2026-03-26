"""Tests for building_blocks.types modules."""
from __future__ import annotations

from building_blocks.context import create_ifc_project
from building_blocks.types.wall_types import create_exterior_wall_type, create_interior_wall_type
from building_blocks.types.column_types import create_concrete_column_type, create_circular_column_type
from building_blocks.types.beam_types import create_concrete_beam_type, create_steel_beam_type
from building_blocks.types.door_types import create_single_swing_door_type, create_fire_door_type
from building_blocks.types.window_types import create_standard_window_type, create_double_glazed_window_type


def test_wall_types():
    ifc, _ = create_ifc_project()
    ext_type = create_exterior_wall_type(ifc)
    assert ext_type is not None
    assert ext_type.is_a("IfcWallType")

    int_type = create_interior_wall_type(ifc)
    assert int_type is not None
    assert int_type.is_a("IfcWallType")


def test_column_types():
    ifc, _ = create_ifc_project()
    rect_type = create_concrete_column_type(ifc)
    assert rect_type is not None
    assert rect_type.is_a("IfcColumnType")

    circ_type = create_circular_column_type(ifc)
    assert circ_type is not None
    assert circ_type.is_a("IfcColumnType")


def test_beam_types():
    ifc, _ = create_ifc_project()
    rc_type = create_concrete_beam_type(ifc)
    assert rc_type is not None
    assert rc_type.is_a("IfcBeamType")

    stl_type = create_steel_beam_type(ifc)
    assert stl_type is not None
    assert stl_type.is_a("IfcBeamType")


def test_door_types():
    ifc, _ = create_ifc_project()
    single_type = create_single_swing_door_type(ifc)
    assert single_type is not None
    assert single_type.is_a("IfcDoorType")

    fire_type = create_fire_door_type(ifc)
    assert fire_type is not None
    assert fire_type.is_a("IfcDoorType")


def test_window_types():
    ifc, _ = create_ifc_project()
    std_type = create_standard_window_type(ifc)
    assert std_type is not None
    assert std_type.is_a("IfcWindowType")

    dg_type = create_double_glazed_window_type(ifc)
    assert dg_type is not None
    assert dg_type.is_a("IfcWindowType")
