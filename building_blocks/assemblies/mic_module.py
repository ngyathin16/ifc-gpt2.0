"""
MiC (Modular integrated Construction) module assembly.

Creates a parametric MiC room module using existing primitives (walls, slab,
door, window).  Dimensions come from mic_catalog.py which holds real measured
values extracted from 49 individual IFC files of the HSK MiC project.

A MiC module is a factory-built volumetric unit containing:
  - Four perimeter walls (concrete, structural)
  - A floor slab
  - A ceiling slab
  - A door (entry)
  - Optional window(s) on the facade wall

The module is placed at a given origin and storey, oriented by *rotation*
(degrees counter-clockwise from the X-axis).
"""
from __future__ import annotations

import math

import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.aggregate
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial

from building_blocks.mic_catalog import (
    MiCModuleDims,
    MIC_CATALOG,
    get_by_type_code,
    get_typical_dims,
)
from building_blocks.primitives.door import create_door
from building_blocks.primitives.slab import create_slab
from building_blocks.primitives.wall import create_wall
from building_blocks.primitives.window import create_window
from building_blocks.psets import apply_space_common_pset


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_mic_module(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    origin: tuple[float, float] = (0.0, 0.0),
    rotation_deg: float = 0.0,
    mic_type_code: str | None = None,
    category: str | None = None,
    width: float | None = None,
    depth: float | None = None,
    height: float | None = None,
    wall_thickness: float = 0.15,
    slab_thickness: float = 0.15,
    door_width: float = 0.9,
    door_height: float = 2.1,
    window_width: float = 1.2,
    window_height: float = 1.2,
    window_sill: float = 0.9,
    include_floor_slab: bool = True,
    include_ceiling_slab: bool = True,
    name_prefix: str = "MiC",
) -> dict:
    """
    Create a complete MiC room module assembly.

    Dimension resolution order:
      1. Explicit ``width``/``depth``/``height`` override everything.
      2. ``mic_type_code`` looks up real measured dims from mic_catalog.
      3. ``category`` picks the first matching catalog entry.
      4. Fallback: 2.4 × 4.0 × 3.0 m (generic bedroom box).

    Args:
        ifc: Open IFC4 file.
        contexts: Dict with at least ``"body"`` and ``"axis"`` contexts.
        storey: IfcBuildingStorey to contain the module.
        origin: (x, y) of the module's bottom-left corner in world metres.
        rotation_deg: Counter-clockwise rotation in degrees.
        mic_type_code: MiC type code, e.g. ``"1.3_MB1L"``.
        category: Room category fallback, e.g. ``"master_bedroom"``.
        width / depth / height: Explicit overrides (metres).
        wall_thickness: Module wall thickness (default 150 mm).
        slab_thickness: Floor/ceiling slab thickness (default 150 mm).
        include_floor_slab: Create a floor slab.
        include_ceiling_slab: Create a ceiling slab.

    Returns:
        dict with keys ``walls``, ``doors``, ``windows``, ``slabs``, ``space``,
        ``dims`` (resolved MiCModuleDims or None).
    """
    dims = _resolve_dims(mic_type_code, category)

    w = width if width is not None else (dims.width_m if dims else 2.4)
    d = depth if depth is not None else (dims.depth_m if dims else 4.0)
    h = height if height is not None else (dims.height_m if dims else 3.0)

    cat_name = dims.category if dims else (category or "room")
    n_doors = dims.typical_door_count if dims else 1
    n_windows = dims.typical_window_count if dims else (1 if w >= 2.0 else 0)
    has_window = dims.has_window if dims else (w >= 2.0)

    ox, oy = origin
    rad = math.radians(rotation_deg)
    cos_r = math.cos(rad)
    sin_r = math.sin(rad)

    def _rot(x: float, y: float) -> tuple[float, float]:
        """Rotate a local point around the origin."""
        return (ox + x * cos_r - y * sin_r,
                oy + x * sin_r + y * cos_r)

    t = wall_thickness

    # Corner points (local frame, then rotated to world)
    p_sw = _rot(0, 0)
    p_se = _rot(w, 0)
    p_ne = _rot(w, d)
    p_nw = _rot(0, d)

    walls: list = []
    doors: list = []
    windows: list = []
    slabs: list = []

    # --- Perimeter walls ---
    wall_south = create_wall(ifc, contexts, storey,
                             p1=p_sw, p2=p_se, height=h, thickness=t,
                             name=f"{name_prefix}_WallS", is_external=True)
    walls.append(wall_south)

    walls.append(create_wall(ifc, contexts, storey,
                             p1=p_se, p2=p_ne, height=h, thickness=t,
                             name=f"{name_prefix}_WallE", is_external=True))

    walls.append(create_wall(ifc, contexts, storey,
                             p1=p_ne, p2=p_nw, height=h, thickness=t,
                             name=f"{name_prefix}_WallN", is_external=True))

    walls.append(create_wall(ifc, contexts, storey,
                             p1=p_nw, p2=p_sw, height=h, thickness=t,
                             name=f"{name_prefix}_WallW", is_external=True))

    # --- Door on south wall (centered) ---
    door_pos = w / 2.0
    for i in range(n_doors):
        offset = 0.0 if n_doors == 1 else (i - (n_doors - 1) / 2.0) * (door_width + 0.3)
        doors.append(create_door(
            ifc, contexts, storey,
            host_wall=wall_south,
            distance_along_wall=door_pos + offset,
            sill_height=0.0,
            width=door_width,
            height=min(door_height, h - 0.1),
            name=f"{name_prefix}_Door{i+1}",
            wall_thickness=t,
        ))

    # --- Window(s) on north wall (facade side) ---
    if has_window and n_windows > 0:
        north_wall = walls[2]  # WallN
        spacing = w / (n_windows + 1)
        for i in range(n_windows):
            win_pos = spacing * (i + 1)
            if win_pos - window_width / 2 < t + 0.1:
                continue
            if win_pos + window_width / 2 > w - t - 0.1:
                continue
            windows.append(create_window(
                ifc, contexts, storey,
                host_wall=north_wall,
                distance_along_wall=win_pos,
                sill_height=window_sill,
                width=window_width,
                height=min(window_height, h - window_sill - 0.1),
                name=f"{name_prefix}_Win{i+1}",
                wall_thickness=t,
            ))

    # --- Floor slab ---
    if include_floor_slab:
        slab_pts = [_rot(t, t), _rot(w - t, t),
                    _rot(w - t, d - t), _rot(t, d - t)]
        slabs.append(create_slab(
            ifc, contexts, storey,
            boundary_points=slab_pts,
            depth=slab_thickness,
            elevation=0.0,
            name=f"{name_prefix}_Floor",
        ))

    # --- Ceiling slab ---
    if include_ceiling_slab:
        ceil_pts = [_rot(t, t), _rot(w - t, t),
                    _rot(w - t, d - t), _rot(t, d - t)]
        slabs.append(create_slab(
            ifc, contexts, storey,
            boundary_points=ceil_pts,
            depth=slab_thickness,
            elevation=h - slab_thickness,
            name=f"{name_prefix}_Ceiling",
        ))

    # --- IfcSpace for the room ---
    space = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcSpace",
        name=f"{name_prefix}_{cat_name}",
        predefined_type="INTERNAL",
    )
    ifcopenshell.api.aggregate.assign_object(
        ifc, products=[space], relating_object=storey,
    )
    apply_space_common_pset(ifc, space, reference=name_prefix, category=cat_name.upper())

    return {
        "walls": walls,
        "doors": doors,
        "windows": windows,
        "slabs": slabs,
        "space": space,
        "dims": dims,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_dims(
    mic_type_code: str | None,
    category: str | None,
) -> MiCModuleDims | None:
    """Resolve module dimensions from type code or category."""
    if mic_type_code:
        dims = get_by_type_code(mic_type_code)
        if dims is not None:
            return dims
    if category:
        return get_typical_dims(category)
    return None


def list_mic_types() -> list[dict[str, str | float]]:
    """Return a summary list of all available MiC module types.

    Useful for LLM prompts and UI selection.
    """
    return [
        {
            "type_code": m.mic_type_code,
            "label": m.label,
            "category": m.category,
            "width_m": m.width_m,
            "depth_m": m.depth_m,
            "height_m": m.height_m,
        }
        for m in MIC_CATALOG
    ]
