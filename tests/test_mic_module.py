"""Tests for building_blocks/assemblies/mic_module.py — MiC module assembly."""
from __future__ import annotations

import ifcopenshell

from building_blocks.assemblies.mic_module import (
    create_mic_module,
    list_mic_types,
)
from building_blocks.mic_catalog import MIC_CATALOG


class TestCreateMicModuleBasic:
    """Basic creation tests — every module must produce valid IFC."""

    def test_default_module(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_mic_module(ifc, contexts, storey)
        assert len(result["walls"]) == 4
        assert len(result["doors"]) >= 1
        assert len(result["slabs"]) == 2  # floor + ceiling
        assert result["space"] is not None
        # Verify all walls are IfcWall
        for w in result["walls"]:
            assert w.is_a("IfcWall")

    def test_by_type_code(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_mic_module(
            ifc, contexts, storey,
            mic_type_code="1_MB1R",
            name_prefix="MB1R",
        )
        assert result["dims"] is not None
        assert result["dims"].category == "master_bedroom"
        assert len(result["walls"]) == 4

    def test_by_category(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_mic_module(
            ifc, contexts, storey,
            category="kitchen",
            name_prefix="KT",
        )
        assert result["dims"] is not None
        assert result["dims"].category == "kitchen"

    def test_explicit_dimensions(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_mic_module(
            ifc, contexts, storey,
            width=3.0, depth=5.0, height=2.8,
            name_prefix="Custom",
        )
        assert len(result["walls"]) == 4
        assert len(result["slabs"]) == 2

    def test_no_slabs(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_mic_module(
            ifc, contexts, storey,
            include_floor_slab=False,
            include_ceiling_slab=False,
        )
        assert len(result["slabs"]) == 0

    def test_no_floor_slab_only(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_mic_module(
            ifc, contexts, storey,
            include_floor_slab=False,
            include_ceiling_slab=True,
        )
        assert len(result["slabs"]) == 1


class TestMicModuleGeometry:
    """Geometry and placement tests."""

    def test_origin_offset(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_mic_module(
            ifc, contexts, storey,
            origin=(10.0, 20.0),
            width=3.0, depth=4.0,
            name_prefix="Offset",
        )
        assert len(result["walls"]) == 4

    def test_rotation(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_mic_module(
            ifc, contexts, storey,
            origin=(0.0, 0.0),
            rotation_deg=90.0,
            width=3.0, depth=4.0,
            name_prefix="Rotated",
        )
        assert len(result["walls"]) == 4


class TestMicModuleOpenings:
    """Door and window placement tests."""

    def test_living_kitchen_has_multiple_windows(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_mic_module(
            ifc, contexts, storey,
            mic_type_code="3.1_LK1L",
            name_prefix="LK",
        )
        assert len(result["windows"]) >= 1  # Should have windows
        assert len(result["doors"]) >= 1

    def test_utility_no_windows(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_mic_module(
            ifc, contexts, storey,
            mic_type_code="7.0_EMR1",
            name_prefix="EMR",
        )
        assert len(result["windows"]) == 0  # Utility rooms have no windows

    def test_bedroom_has_window(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_mic_module(
            ifc, contexts, storey,
            mic_type_code="5_BR1",
            name_prefix="BR",
        )
        assert len(result["windows"]) >= 1


class TestMicModuleSpace:
    """IfcSpace creation tests."""

    def test_space_created(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_mic_module(
            ifc, contexts, storey,
            category="master_bedroom",
            name_prefix="MB",
        )
        space = result["space"]
        assert space.is_a("IfcSpace")
        assert "MB" in space.Name


class TestMicModuleSpatialContainment:
    """All elements must be assigned to the storey."""

    def test_all_contained(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_mic_module(
            ifc, contexts, storey,
            mic_type_code="1_MB1R",
            name_prefix="ContainTest",
        )
        # Check spatial containment for walls
        for wall in result["walls"]:
            rels = wall.ContainedInStructure
            assert len(rels) > 0, f"Wall {wall.Name} not contained"

        # Check doors
        for door in result["doors"]:
            rels = door.ContainedInStructure
            assert len(rels) > 0, f"Door {door.Name} not contained"


class TestMicModuleIFCValidity:
    """The generated IFC must be parseable and valid."""

    def test_ifc_roundtrip(self, ifc_setup, tmp_path):
        ifc, contexts, storey = ifc_setup
        create_mic_module(
            ifc, contexts, storey,
            mic_type_code="4_KTL",
            name_prefix="Kitchen",
        )
        out = tmp_path / "mic_test.ifc"
        ifc.write(str(out))
        # Re-read and verify
        ifc2 = ifcopenshell.open(str(out))
        walls = ifc2.by_type("IfcWall")
        assert len(walls) == 4
        doors = ifc2.by_type("IfcDoor")
        assert len(doors) >= 1
        slabs = ifc2.by_type("IfcSlab")
        assert len(slabs) >= 2

    def test_multiple_modules_same_file(self, ifc_setup, tmp_path):
        ifc, contexts, storey = ifc_setup
        # Place two modules side by side
        create_mic_module(ifc, contexts, storey,
                          origin=(0.0, 0.0), mic_type_code="1_MB1R",
                          name_prefix="MB_A")
        create_mic_module(ifc, contexts, storey,
                          origin=(3.0, 0.0), mic_type_code="5_BR1",
                          name_prefix="BR_B")
        out = tmp_path / "mic_multi.ifc"
        ifc.write(str(out))
        ifc2 = ifcopenshell.open(str(out))
        assert len(ifc2.by_type("IfcWall")) == 8
        assert len(ifc2.by_type("IfcSpace")) == 2


class TestListMicTypes:
    def test_returns_all_types(self):
        types = list_mic_types()
        assert len(types) >= 33

    def test_type_dict_keys(self):
        types = list_mic_types()
        for t in types:
            assert "type_code" in t
            assert "label" in t
            assert "category" in t
            assert "width_m" in t
            assert "depth_m" in t
            assert "height_m" in t

    def test_all_type_codes_in_catalog(self):
        types = list_mic_types()
        catalog_codes = {m.mic_type_code for m in MIC_CATALOG}
        for t in types:
            assert t["type_code"] in catalog_codes
