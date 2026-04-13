"""Tests for building_blocks/assemblies/ — higher-level building kits."""
from __future__ import annotations

from building_blocks.assemblies.structural_grid import create_structural_grid
from building_blocks.assemblies.stair_core import create_stair_core
from building_blocks.assemblies.toilet_core import create_toilet_core
from building_blocks.assemblies.apartment_unit import create_apartment_unit
from building_blocks.assemblies.facade_bay import create_facade_bay
from building_blocks.assemblies.roof_assembly import create_roof_assembly


class TestStructuralGrid:
    def test_basic_grid(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_structural_grid(
            ifc, contexts, storey,
            x_positions=[0.0, 6.0, 12.0],
            y_positions=[0.0, 8.0],
            storey_height=3.0,
        )
        # 3x2 = 6 columns
        assert len(result["columns"]) == 6
        # X beams: 2 per Y line × 2 Y lines = 4
        # Y beams: 1 per X line × 3 X lines = 3
        assert len(result["beams"]) == 7
        for col in result["columns"]:
            assert col.is_a("IfcColumn")
        for beam in result["beams"]:
            assert beam.is_a("IfcBeam")

    def test_single_bay(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_structural_grid(
            ifc, contexts, storey,
            x_positions=[0.0, 6.0],
            y_positions=[0.0, 8.0],
        )
        assert len(result["columns"]) == 4
        assert len(result["beams"]) == 4


class TestStairCore:
    def test_basic_stair_core(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_stair_core(
            ifc, contexts, storey,
            origin=(0.0, 0.0),
            stair_width=1.2,
            stair_length=4.5,
            storey_height=3.0,
            num_risers=18,
        )
        assert result["stair"].is_a("IfcStairFlight")
        assert len(result["walls"]) == 3
        assert len(result["railings"]) == 2
        assert result["landing"].is_a("IfcSlab")

    def test_no_walls_no_railings(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_stair_core(
            ifc, contexts, storey,
            origin=(0.0, 0.0),
            include_walls=False,
            include_railings=False,
        )
        assert len(result["walls"]) == 0
        assert len(result["railings"]) == 0
        assert result["stair"] is not None


class TestToiletCore:
    def test_basic_toilet(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_toilet_core(
            ifc, contexts, storey,
            origin=(0.0, 0.0),
            width=2.0,
            depth=2.5,
        )
        assert len(result["walls"]) == 4
        assert result["door"].is_a("IfcDoor")
        assert result["space"].is_a("IfcSpace")
        assert result["slab"] is None

    def test_with_floor(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_toilet_core(
            ifc, contexts, storey,
            origin=(5.0, 5.0),
            include_floor_slab=True,
        )
        assert result["slab"] is not None
        assert result["slab"].is_a("IfcSlab")


class TestApartmentUnit:
    def test_basic_apartment(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_apartment_unit(
            ifc, contexts, storey,
            origin=(0.0, 0.0),
            width=6.0,
            depth=8.0,
        )
        # 4 perimeter + 1 partition = 5 walls
        assert len(result["walls"]) == 5
        # Front door + bathroom door = 2
        assert len(result["doors"]) == 2
        # Should have at least 1 window
        assert len(result["windows"]) >= 1
        # Living + Bathroom = 2 spaces
        assert len(result["spaces"]) == 2
        assert result["slab"] is None

    def test_no_bathroom(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_apartment_unit(
            ifc, contexts, storey,
            origin=(0.0, 0.0),
            include_bathroom=False,
        )
        # 4 perimeter walls only
        assert len(result["walls"]) == 4
        # Front door only
        assert len(result["doors"]) == 1
        assert len(result["spaces"]) == 1

    def test_with_floor_slab(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_apartment_unit(
            ifc, contexts, storey,
            origin=(0.0, 0.0),
            include_floor_slab=True,
        )
        assert result["slab"] is not None
        assert result["slab"].is_a("IfcSlab")


class TestFacadeBay:
    def test_basic_facade(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_facade_bay(
            ifc, contexts, storey,
            p1=(0.0, 0.0),
            p2=(12.0, 0.0),
            num_windows=3,
            window_width=1.5,
        )
        assert result["wall"].is_a("IfcWall")
        assert len(result["windows"]) == 3
        assert result["beam"] is None

    def test_with_spandrel(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_facade_bay(
            ifc, contexts, storey,
            p1=(0.0, 0.0),
            p2=(10.0, 0.0),
            num_windows=2,
            include_spandrel_beam=True,
        )
        assert result["beam"] is not None
        assert result["beam"].is_a("IfcBeam")

    def test_no_windows(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        result = create_facade_bay(
            ifc, contexts, storey,
            p1=(0.0, 0.0),
            p2=(5.0, 0.0),
            num_windows=0,
        )
        assert len(result["windows"]) == 0

    def test_custom_window_spacing(self, ifc_setup):
        """Cover the window_spacing override branch (lines 82-84)."""
        ifc, contexts, storey = ifc_setup
        result = create_facade_bay(
            ifc, contexts, storey,
            p1=(0.0, 0.0),
            p2=(12.0, 0.0),
            num_windows=2,
            window_width=1.5,
            window_spacing=4.0,
        )
        assert result["wall"].is_a("IfcWall")
        assert len(result["windows"]) == 2

    def test_windows_clipped_at_edges(self, ifc_setup):
        """Cover window edge-clipping branches (lines 89, 91).

        Use a very short wall with many windows so that some windows
        are too close to the start or end edge and get skipped.
        """
        ifc, contexts, storey = ifc_setup
        result = create_facade_bay(
            ifc, contexts, storey,
            p1=(0.0, 0.0),
            p2=(3.0, 0.0),
            num_windows=5,
            window_width=1.5,
        )
        # With a 3m wall and 5 × 1.5m windows, not all will fit
        assert len(result["windows"]) < 5


class TestRoofAssembly:
    def test_flat_roof(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        boundary = [(0, 0), (10, 0), (10, 8), (0, 8)]
        result = create_roof_assembly(
            ifc, contexts, storey,
            boundary_points=boundary,
            elevation=3.0,
            roof_type="FLAT",
        )
        assert result["roof"].is_a("IfcRoof")
        assert len(result["parapets"]) == 0
        assert len(result["railings"]) == 0

    def test_flat_with_parapet(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        boundary = [(0, 0), (10, 0), (10, 8), (0, 8)]
        result = create_roof_assembly(
            ifc, contexts, storey,
            boundary_points=boundary,
            elevation=3.0,
            roof_type="FLAT",
            include_parapet=True,
        )
        assert len(result["parapets"]) == 4
        for p in result["parapets"]:
            assert p.is_a("IfcWall")

    def test_flat_with_railing(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        boundary = [(0, 0), (10, 0), (10, 8), (0, 8)]
        result = create_roof_assembly(
            ifc, contexts, storey,
            boundary_points=boundary,
            elevation=3.0,
            roof_type="FLAT",
            include_railing=True,
        )
        assert len(result["railings"]) == 1
        assert result["railings"][0].is_a("IfcRailing")

    def test_gable_roof(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        boundary = [(0, 0), (10, 0), (10, 8), (0, 8)]
        result = create_roof_assembly(
            ifc, contexts, storey,
            boundary_points=boundary,
            elevation=3.0,
            roof_type="GABLE",
            ridge_height=2.0,
        )
        assert result["roof"].is_a("IfcRoof")

    def test_hip_roof(self, ifc_setup):
        ifc, contexts, storey = ifc_setup
        boundary = [(0, 0), (12, 0), (12, 10), (0, 10)]
        result = create_roof_assembly(
            ifc, contexts, storey,
            boundary_points=boundary,
            elevation=6.0,
            roof_type="HIP",
        )
        assert result["roof"].is_a("IfcRoof")
