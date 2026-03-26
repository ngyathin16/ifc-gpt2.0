"""Higher-level building assembly kits."""
from __future__ import annotations

from building_blocks.assemblies.structural_grid import create_structural_grid
from building_blocks.assemblies.stair_core import create_stair_core
from building_blocks.assemblies.toilet_core import create_toilet_core
from building_blocks.assemblies.apartment_unit import create_apartment_unit
from building_blocks.assemblies.facade_bay import create_facade_bay
from building_blocks.assemblies.roof_assembly import create_roof_assembly

__all__ = [
    "create_structural_grid",
    "create_stair_core",
    "create_toilet_core",
    "create_apartment_unit",
    "create_facade_bay",
    "create_roof_assembly",
]
