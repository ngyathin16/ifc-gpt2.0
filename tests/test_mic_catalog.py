"""Tests for building_blocks/mic_catalog.py — MiC room dimension catalog."""
from __future__ import annotations

from building_blocks.mic_catalog import (
    MIC_CATALOG,
    MIC_TYPE_CODE_INDEX,
    ROOM_LABEL_TO_CATEGORY,
    classify_room,
    expected_size_range,
    get_all_dims_for_category,
    get_by_type_code,
    get_opening_defaults,
    get_typical_dims,
)


class TestClassifyRoom:
    def test_direct_match(self):
        assert classify_room("bedroom") == "bedroom"
        assert classify_room("kitchen") == "kitchen"
        assert classify_room("bathroom") == "bathroom"
        assert classify_room("toilet") == "toilet"
        assert classify_room("master bedroom") == "master_bedroom"

    def test_case_insensitive(self):
        assert classify_room("Bedroom") == "bedroom"
        assert classify_room("KITCHEN") == "kitchen"
        assert classify_room("Master Bedroom") == "master_bedroom"

    def test_substring_match(self):
        assert classify_room("Large Master Bedroom") == "master_bedroom"
        assert classify_room("Guest Bathroom") == "bathroom"
        assert classify_room("Open Kitchen") == "kitchen"

    def test_whitespace_handling(self):
        assert classify_room("  bedroom  ") == "bedroom"
        assert classify_room("  master bedroom  ") == "master_bedroom"

    def test_unknown_label(self):
        assert classify_room("swimming pool") == "unknown"
        assert classify_room("") == "unknown"

    def test_corridor_variants(self):
        assert classify_room("corridor") == "corridor"
        assert classify_room("hallway") == "corridor"
        assert classify_room("lobby") == "corridor"

    def test_utility_variants(self):
        assert classify_room("utility") == "utility"
        assert classify_room("storage") == "utility"
        assert classify_room("laundry") == "utility"

    def test_living_variants(self):
        assert classify_room("living room") == "living_kitchen"
        assert classify_room("living/kitchen") == "living_kitchen"
        assert classify_room("living/dining") == "living_dining"
        assert classify_room("dining room") == "living_dining"


class TestGetTypicalDims:
    def test_known_category(self):
        dims = get_typical_dims("bedroom")
        assert dims is not None
        assert dims.width_m > 0
        assert dims.depth_m > 0
        assert dims.height_m > 0
        assert dims.has_window is True

    def test_bathroom_category(self):
        dims = get_typical_dims("bathroom")
        assert dims is not None
        assert dims.width_m < dims.depth_m  # Bathrooms are typically deeper
        assert dims.has_door is True

    def test_toilet_category(self):
        dims = get_typical_dims("toilet")
        assert dims is not None
        assert dims.has_window is True  # HK MiC toilets have windows (measured)

    def test_unknown_category(self):
        assert get_typical_dims("swimming_pool") is None

    def test_utility_category(self):
        dims = get_typical_dims("utility")
        assert dims is not None
        assert dims.has_window is False


class TestGetAllDimsForCategory:
    def test_master_bedroom_variants(self):
        dims = get_all_dims_for_category("master_bedroom")
        assert len(dims) >= 2  # Multiple MB variants

    def test_bathroom_variants(self):
        dims = get_all_dims_for_category("bathroom")
        assert len(dims) >= 2

    def test_unknown_category_empty(self):
        assert get_all_dims_for_category("nonexistent") == []


class TestGetOpeningDefaults:
    def test_bedroom_has_door_and_window(self):
        defaults = get_opening_defaults("bedroom")
        assert defaults["doors"] >= 1
        assert defaults["windows"] >= 1

    def test_toilet_has_door_and_window(self):
        defaults = get_opening_defaults("toilet")
        assert defaults["doors"] >= 1
        assert defaults["windows"] >= 1  # HK MiC toilets have windows

    def test_living_kitchen_multiple_openings(self):
        defaults = get_opening_defaults("living_kitchen")
        assert defaults["doors"] >= 2
        assert defaults["windows"] >= 2

    def test_unknown_category_defaults(self):
        defaults = get_opening_defaults("nonexistent")
        assert defaults["doors"] == 1
        assert defaults["windows"] == 0


class TestExpectedSizeRange:
    def test_bedroom_range(self):
        r = expected_size_range("bedroom")
        assert r is not None
        min_area, max_area = r
        assert min_area > 0
        assert max_area > min_area
        # Bedroom should be between ~6 and ~18 m²
        assert min_area < 15
        assert max_area > 8

    def test_unknown_category(self):
        assert expected_size_range("nonexistent") is None

    def test_all_catalog_categories_have_ranges(self):
        categories = set(m.category for m in MIC_CATALOG)
        for cat in categories:
            r = expected_size_range(cat)
            assert r is not None, f"No size range for category: {cat}"
            assert r[0] > 0
            assert r[1] > r[0]


class TestGetByTypeCode:
    def test_known_code(self):
        dims = get_by_type_code("1_MB1R")
        assert dims is not None
        assert dims.category == "master_bedroom"
        assert abs(dims.width_m - 2.385) < 0.01

    def test_living_kitchen_code(self):
        dims = get_by_type_code("3.1_LK1L")
        assert dims is not None
        assert dims.category == "living_kitchen"
        assert dims.width_m > 2.5  # real measured ~2.755m

    def test_unknown_code(self):
        assert get_by_type_code("99_FAKE") is None

    def test_all_catalog_entries_in_index(self):
        for mod in MIC_CATALOG:
            assert mod.mic_type_code in MIC_TYPE_CODE_INDEX
            assert MIC_TYPE_CODE_INDEX[mod.mic_type_code] is mod

    def test_type_codes_unique(self):
        codes = [m.mic_type_code for m in MIC_CATALOG]
        assert len(codes) == len(set(codes)), "Duplicate type codes found"


class TestCatalogIntegrity:
    def test_catalog_not_empty(self):
        assert len(MIC_CATALOG) > 0

    def test_catalog_has_all_33_unique_types(self):
        assert len(MIC_CATALOG) >= 33

    def test_all_modules_have_positive_dims(self):
        for mod in MIC_CATALOG:
            assert mod.width_m > 0, f"{mod.label} has zero width"
            assert mod.depth_m > 0, f"{mod.label} has zero depth"
            assert mod.height_m > 0, f"{mod.label} has zero height"

    def test_all_modules_have_type_code(self):
        for mod in MIC_CATALOG:
            assert mod.mic_type_code, f"{mod.label} has empty type code"

    def test_heights_in_realistic_range(self):
        for mod in MIC_CATALOG:
            assert 2.5 < mod.height_m < 4.0, (
                f"{mod.label} height {mod.height_m}m outside 2.5-4.0m range"
            )

    def test_room_label_map_not_empty(self):
        assert len(ROOM_LABEL_TO_CATEGORY) > 10

    def test_all_label_map_targets_exist_in_catalog(self):
        catalog_categories = set(m.category for m in MIC_CATALOG)
        # Non-structural categories that don't need MiC modules
        non_mic = {"balcony", "corridor", "stairwell", "lift", "garage"}
        for label, cat in ROOM_LABEL_TO_CATEGORY.items():
            if cat not in non_mic:
                assert cat in catalog_categories, (
                    f"Label '{label}' maps to category '{cat}' "
                    f"which has no entry in MIC_CATALOG"
                )

    def test_all_categories_covered(self):
        cats = {m.category for m in MIC_CATALOG}
        expected = {
            "master_bedroom", "bathroom", "living_kitchen",
            "living_dining", "kitchen", "bedroom", "toilet", "utility",
        }
        assert expected.issubset(cats)
