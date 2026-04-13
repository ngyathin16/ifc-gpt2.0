"""Tests for building_blocks/psets.py — cover all optional parameter branches."""
from __future__ import annotations

import ifcopenshell.api.pset

from building_blocks.psets import (
    apply_wall_common_pset,
    apply_door_common_pset,
    apply_window_common_pset,
    apply_column_common_pset,
    apply_slab_common_pset,
    apply_beam_common_pset,
    apply_space_common_pset,
    apply_roof_common_pset,
    apply_stair_common_pset,
)


def _get_pset_props(ifc, element, pset_name: str) -> dict:
    """Helper: extract property values from a named Pset on an element."""
    for rel in ifc.by_type("IfcRelDefinesByProperties"):
        if element not in rel.RelatedObjects:
            continue
        pset = rel.RelatingPropertyDefinition
        if hasattr(pset, "Name") and pset.Name == pset_name:
            return {
                p.Name: (
                    p.NominalValue.wrappedValue if p.NominalValue else None
                )
                for p in pset.HasProperties
            }
    return {}


class TestWallCommonPset:
    def test_defaults_only(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        wall = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcWall", name="W")
        apply_wall_common_pset(ifc, wall)
        props = _get_pset_props(ifc, wall, "Pset_WallCommon")
        assert props["IsExternal"] is True

    def test_all_optional_params(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        wall = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcWall", name="W")
        apply_wall_common_pset(
            ifc, wall,
            is_external=False,
            fire_rating="2HR",
            acoustic_rating="STC50",
            thermal_transmittance=0.35,
        )
        props = _get_pset_props(ifc, wall, "Pset_WallCommon")
        assert props["IsExternal"] is False
        assert props["FireRating"] == "2HR"
        assert props["AcousticRating"] == "STC50"
        assert props["ThermalTransmittance"] == 0.35


class TestDoorCommonPset:
    def test_defaults_only(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        door = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcDoor", name="D")
        apply_door_common_pset(ifc, door)
        props = _get_pset_props(ifc, door, "Pset_DoorCommon")
        assert props["IsExternal"] is False

    def test_all_optional_params(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        door = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcDoor", name="D")
        apply_door_common_pset(
            ifc, door,
            fire_rating="1HR",
            is_external=True,
            security_rating="Level3",
        )
        props = _get_pset_props(ifc, door, "Pset_DoorCommon")
        assert props["FireRating"] == "1HR"
        assert props["IsExternal"] is True
        assert props["SecurityRating"] == "Level3"


class TestWindowCommonPset:
    def test_defaults_only(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        win = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcWindow", name="Win")
        apply_window_common_pset(ifc, win)
        props = _get_pset_props(ifc, win, "Pset_WindowCommon")
        assert props["IsExternal"] is True

    def test_all_optional_params(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        win = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcWindow", name="Win")
        apply_window_common_pset(
            ifc, win,
            fire_rating="30min",
            is_external=False,
            thermal_transmittance=1.2,
        )
        props = _get_pset_props(ifc, win, "Pset_WindowCommon")
        assert props["FireRating"] == "30min"
        assert props["IsExternal"] is False
        assert props["ThermalTransmittance"] == 1.2


class TestColumnCommonPset:
    def test_with_fire_rating(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        col = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcColumn", name="C")
        apply_column_common_pset(ifc, col, fire_rating="2HR")
        props = _get_pset_props(ifc, col, "Pset_ColumnCommon")
        assert props["FireRating"] == "2HR"


class TestSlabCommonPset:
    def test_with_fire_rating(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        slab = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcSlab", name="S")
        apply_slab_common_pset(ifc, slab, fire_rating="1HR")
        props = _get_pset_props(ifc, slab, "Pset_SlabCommon")
        assert props["FireRating"] == "1HR"


class TestBeamCommonPset:
    def test_with_fire_rating(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        beam = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcBeam", name="B")
        apply_beam_common_pset(ifc, beam, fire_rating="1HR")
        props = _get_pset_props(ifc, beam, "Pset_BeamCommon")
        assert props["FireRating"] == "1HR"


class TestRoofCommonPset:
    def test_with_fire_rating(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        roof = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcRoof", name="R")
        apply_roof_common_pset(ifc, roof, fire_rating="30min")
        props = _get_pset_props(ifc, roof, "Pset_RoofCommon")
        assert props["FireRating"] == "30min"


class TestSpaceCommonPset:
    def test_with_reference_and_category(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        space = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcSpace", name="Sp")
        apply_space_common_pset(ifc, space, reference="A101", category="Office")
        props = _get_pset_props(ifc, space, "Pset_SpaceCommon")
        assert props["Reference"] == "A101"
        assert props["Category"] == "Office"


class TestStairCommonPset:
    def test_with_all_optional_params(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        stair = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcStair", name="St")
        apply_stair_common_pset(
            ifc, stair,
            fire_rating="1HR",
            number_of_risers=18,
            riser_height=0.167,
            tread_length=0.28,
        )
        props = _get_pset_props(ifc, stair, "Pset_StairCommon")
        assert props["FireRating"] == "1HR"
        assert props["NumberOfRiser"] == 18
        assert abs(props["RiserHeight"] - 0.167) < 1e-6
        assert abs(props["TreadLength"] - 0.28) < 1e-6
