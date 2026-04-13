# IFC-GPT v2 — Full Rebuild Plan

> **For Windsurf:** This is a from-scratch rebuild specification. Read every section before writing a single line. Follow the tech choices exactly — they are not suggestions. Where verbatim code is given, use it. Where a description is given, implement it to the standard described. The goal is a production-grade, Blender-free BIM-AI web application.

---

## 1. Lessons From IFC-GPT v1

| Mistake | Impact | Fix in v2 |
|---|---|---|
| Runtime dependency on Blender/Bonsai socket | Cannot deploy without a desktop app running | Pure Python IFC generation via IfcOpenShell |
| IFC generation tool surface too narrow (`create_wall`, `create_slab` only) | Cannot author complex buildings | Rich parametric block library |
| Validation coupled to Blender | Fragile, no CI | `ifctester` + IDS files, pure Python |
| Fragmented toolchain (CLI + Windsurf + MCP + Blender) | Hard to demo, hard for non-technical users | Single web app |
| MCP-first entry point, no HTTP API | Cannot connect a frontend | FastAPI + SSE from day one |
| No database / no user sessions | Single-user only | Supabase |
| No visual input | Text-only UX bottleneck | Pascal editor drawing canvas |
| 3D model only viewable in Blender | Requires desktop install | ThatOpen IFC viewer in browser |

---

## 2. Final Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Browser (React / Next.js 15)       │
│                                                      │
│  ┌──────────────┐  ┌─────────────────────────────┐  │
│  │ Pascal Editor│  │   ThatOpen IFC Viewer        │  │
│  │ (draw walls, │  │   (@thatopen/components)     │  │
│  │  levels, etc)│  │   - loads .ifc via web-ifc   │  │
│  │             │  │   - element click → GUID      │  │
│  └──────┬───────┘  └────────────────┬────────────┘  │
│         │  BuildingPlan JSON        │  GUID + cmd   │
│  ┌──────▼───────────────────────────▼────────────┐  │
│  │          shadcn/ui + Tailwind CSS + Framer     │  │
│  │          Motion UI Shell                       │  │
│  └──────────────────────┬────────────────────────┘  │
└─────────────────────────│────────────────────────────┘
                          │  REST / SSE
┌─────────────────────────▼────────────────────────────┐
│              FastAPI HTTP Server (Python)             │
│                                                      │
│  POST /api/generate        ← text prompt             │
│  POST /api/build-from-plan ← pascal editor JSON      │
│  POST /api/modify          ← GUID + instruction      │
│  POST /api/voice           ← audio → Whisper → text  │
│  GET  /api/status/{id}/stream ← SSE job stream       │
│  GET  /workspace/{file}    ← serve .ifc files        │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│              LangGraph Agent Pipeline                │
│                                                      │
│  intake → clarify → plan → build → validate → export│
│                                                      │
│  LLM: gpt-5.4-pro (Azure OpenAI or plain OpenAI)    │
│  Tools: building_blocks/* (IfcOpenShell-native)      │
│  Validation: ifctester + IDS files                   │
│  Knowledge: bSDD API retrieval + local block catalog │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│         IfcOpenShell Authoring Backend               │
│                                                      │
│  building_blocks/primitives/  ← root, geometry, pset │
│  building_blocks/elements/    ← typed element makers │
│  building_blocks/assemblies/  ← room kits, cores     │
│  building_blocks/catalog/     ← bSDD-enriched types  │
└──────────────────────────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│              Supabase                                │
│   - user auth (JWT)                                  │
│   - project history (postgres)                       │
│   - IFC file metadata                                │
│   - job queue state                                  │
└──────────────────────────────────────────────────────┘
```

---

## 3. Technology Choices (Explicit & Final)

| Layer | Technology | Why |
|---|---|---|
| IFC generation | **IfcOpenShell Python API** | Native Python, no Blender needed, full IFC4 authoring |
| IFC validation | **ifctester + IDS files** | Official buildingSMART tool, pure Python, CI-compatible |
| LLM | **gpt-5.4-pro** (Azure OpenAI Responses API or OpenAI) | Successor to gpt-5.1-codex-max, better spatial reasoning |
| Agent orchestration | **LangGraph** | Keep from v1; battle-tested for multi-step pipelines |
| HTTP server | **FastAPI + uvicorn** | Already in pyproject.toml, async, SSE support |
| Streaming | **Server-Sent Events (SSE)** | No WS complexity, native browser `EventSource` |
| Frontend framework | **Next.js 15 (App Router)** | React server components, TypeScript, easy API proxying |
| UI component library | **shadcn/ui** | Unstyled primitives, Tailwind-composable, AI-friendly |
| Styling | **Tailwind CSS v4** | Utility-first, pairs perfectly with shadcn |
| Animations | **Framer Motion** | Production-grade motion, dark BIM aesthetic |
| IFC browser rendering | **@thatopen/components + @thatopen/components-front** | Three.js + web-ifc WASM, native IFC loader |
| Visual design input | **Pascal editor (@pascal-app/core)** | Zustand-based node graph, maps to BuildingPlan schema |
| Building block knowledge | **bSDD REST API** (`api.bsdd.buildingsmart.org`) | Official class/property/classification lookups |
| Database | **Supabase** (PostgreSQL + Auth + Storage) | Managed, real-time, free tier, easy FastAPI JWT integration |
| File storage | **Supabase Storage** (for `.ifc` files) | Replaces local `workspace/` dir for multi-user |
| Voice input | **OpenAI Whisper API** | High-fidelity STT, already used in prior INTEGRATION_PLAN |
| Package manager | **uv** (Python) + **npm** (Node) | Keep from v1 |
| MCP | **Optional / dev-only** | Windsurf integration only; not part of runtime |

---

## 4. Repository Structure (Start From Scratch)

```
ifc-gpt-v2/
├── PLAN.md                          # This file
├── AGENTS.md                        # AI agent coding rules for Windsurf
├── pyproject.toml                   # Python project config
├── .env.example                     # All required env vars
├── .gitignore
│
├── api/                             # FastAPI HTTP server
│   ├── __init__.py
│   ├── server.py                    # App factory, CORS, static mounts
│   ├── routes/
│   │   ├── generate.py              # POST /api/generate
│   │   ├── build_from_plan.py       # POST /api/build-from-plan
│   │   ├── modify.py                # POST /api/modify
│   │   ├── voice.py                 # POST /api/voice
│   │   └── status.py                # GET /api/status/{id}/stream (SSE)
│   └── deps.py                      # Supabase JWT verification dependency
│
├── agent/                           # LangGraph pipeline
│   ├── graph.py                     # Main LangGraph definition
│   ├── nodes/
│   │   ├── intake.py
│   │   ├── clarify.py
│   │   ├── plan.py
│   │   ├── build.py                 # Calls building_blocks
│   │   ├── validate.py              # Calls ifctester
│   │   ├── repair.py
│   │   └── export.py
│   ├── schemas.py                   # BuildingPlan Pydantic model (expanded)
│   ├── llm.py                       # gpt-5.4-pro client factory
│   └── prompts/
│       ├── system.txt
│       ├── plan.txt
│       └── repair.txt
│
├── building_blocks/                 # IFC authoring library (IfcOpenShell-native)
│   ├── __init__.py
│   ├── context.py                   # IFC project/site/building/storey setup
│   ├── primitives/
│   │   ├── wall.py
│   │   ├── slab.py
│   │   ├── column.py
│   │   ├── beam.py
│   │   ├── opening.py               # semantic void + fill
│   │   ├── door.py
│   │   ├── window.py
│   │   ├── roof.py
│   │   ├── stair.py
│   │   ├── railing.py
│   │   ├── ramp.py
│   │   ├── curtain_wall.py
│   │   ├── covering.py
│   │   ├── member.py
│   │   └── footing.py
│   ├── types/                       # IfcXxxType definitions + material layer/profile sets
│   │   ├── wall_types.py
│   │   ├── column_types.py
│   │   ├── beam_types.py
│   │   ├── door_types.py
│   │   └── window_types.py
│   ├── assemblies/                  # Higher-level kits
│   │   ├── stair_core.py
│   │   ├── toilet_core.py
│   │   ├── apartment_unit.py
│   │   ├── structural_grid.py
│   │   ├── facade_bay.py
│   │   └── roof_assembly.py
│   ├── psets.py                     # Standard Pset helper: Pset_WallCommon, etc.
│   └── bsdd.py                      # bSDD REST API client for class/property lookup
│
├── validation/
│   ├── runner.py                    # ifctester wrapper
│   └── ids/                         # IDS files
│       ├── base.ids
│       ├── hk_code.ids
│       └── custom.ids
│
├── workspace/                       # Local IFC output (dev only; Supabase Storage in prod)
│
└── web/                             # Next.js 15 frontend
    ├── package.json
    ├── next.config.ts
    ├── tailwind.config.ts
    ├── .env.local
    ├── app/
    │   ├── layout.tsx               # Root layout, fonts, Framer Motion provider
    │   ├── page.tsx                 # Main app shell
    │   ├── api/
    │   │   └── [...proxy]/          # Optional: Next.js proxy to FastAPI
    │   └── (auth)/
    │       ├── login/page.tsx
    │       └── register/page.tsx
    ├── components/
    │   ├── ui/                      # shadcn/ui generated components
    │   ├── IFCViewer.tsx            # ThatOpen viewer (client-only)
    │   ├── VisualEditor.tsx         # Pascal editor canvas
    │   ├── ChatPanel.tsx            # Text + voice prompt input
    │   ├── ModifyPanel.tsx          # GUID-targeted modification form
    │   ├── JobStatusBadge.tsx       # SSE-connected job indicator
    │   └── AppShell.tsx             # Layout: left panel + 3D canvas
    ├── hooks/
    │   ├── useJob.ts                # Polls/streams job status
    │   ├── usePascalEditor.ts       # Pascal editor Zustand store
    │   └── useVoice.ts              # MediaRecorder → Whisper
    ├── lib/
    │   ├── api.ts                   # Typed fetch wrappers for all endpoints
    │   ├── toPlanJSON.ts            # Pascal scene → BuildingPlan converter
    │   └── supabase.ts              # Supabase browser client
    └── types/
        └── building.ts              # Shared BuildingPlan TypeScript types
```

---

## 5. Phase 0 — Project Bootstrap

### 5.1 Python project

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "ifc-gpt-v2"
version = "2.0.0"
requires-python = ">=3.11"
dependencies = [
    # IFC authoring and validation
    "ifcopenshell",
    "ifctester",
    # AI / orchestration
    "langchain>=0.3.0",
    "langchain-core>=0.3.90",
    "langchain-openai>=0.1.0",
    "langgraph>=0.2.0",
    "openai>=1.30.0",
    # HTTP server
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "python-multipart>=0.0.9",     # for audio file uploads
    "sse-starlette>=2.0.0",        # for SSE streaming
    # Database
    "supabase>=2.0.0",
    "python-jose[cryptography]>=3.3.0",  # Supabase JWT verification
    # Utilities
    "pydantic>=2.7.0",
    "python-dotenv>=1.0.0",
    "rich>=13.0.0",
    "httpx>=0.27.0",               # async HTTP for bSDD API calls
    "numpy>=1.26.0",
    "shapely>=2.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.4", "mypy>=1.10"]

[project.scripts]
ifc-gpt = "api.server:main"
```

### 5.2 Environment variables

Create `.env.example`:

```env
# LLM — choose one
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=https://<resource>.cognitiveservices.azure.com/openai/responses?api-version=2025-04-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-5.4-pro
AZURE_OPENAI_API_VERSION=2025-04-01-preview

OPENAI_API_KEY=           # fallback if no Azure

# Supabase
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=   # server-side only
SUPABASE_JWT_SECRET=

# App
FRONTEND_ORIGIN=http://localhost:3000
WORKSPACE_DIR=./workspace
IDS_DIR=./validation/ids
```

### 5.3 Main entry point

Create `main.py` at root:

```python
"""IFC-GPT v2 — entry point.

Usage:
    uv run main.py              # HTTP server (default)
    uv run main.py --port 8080  # Custom port
"""
import sys
import uvicorn

def main():
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8000
    uvicorn.run("api.server:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    main()
```

---

## 6. Phase 1 — IfcOpenShell Authoring Backend

This is the most critical new piece. All IFC is authored in Python without Blender.

### 6.1 Project/context setup (`building_blocks/context.py`)

```python
"""
Sets up the IFC4 project/site/building/storey spatial hierarchy.
All other building_blocks functions receive the IFC file and storey references.
"""
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.aggregate
import ifcopenshell.api.context
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.unit


def create_ifc_project(
    project_name: str = "IFC-GPT Project",
    site_name: str = "Default Site",
    building_name: str = "Building A",
) -> tuple[ifcopenshell.file, dict]:
    """
    Create a blank IFC4 file with Project/Site/Building hierarchy.

    Returns:
        (ifc_file, context_dict) where context_dict has keys:
        - model3d: IfcGeometricRepresentationContext (3D)
        - body:    Model/Body/MODEL_VIEW context
        - axis:    Plan/Axis/GRAPH_VIEW context
        - project, site, building
    """
    ifc = ifcopenshell.file(schema="IFC4")

    # Project
    project = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcProject", name=project_name)
    ifcopenshell.api.unit.assign_unit(ifc, length={"is_metric": True, "raw": "METRES"})

    # Geometric contexts
    model3d = ifcopenshell.api.context.add_context(ifc, context_type="Model")
    body = ifcopenshell.api.context.add_context(
        ifc, context_type="Model", context_identifier="Body",
        target_view="MODEL_VIEW", parent=model3d,
    )
    axis = ifcopenshell.api.context.add_context(
        ifc, context_type="Plan", context_identifier="Axis",
        target_view="GRAPH_VIEW", parent=model3d,
    )

    # Spatial hierarchy
    site = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcSite", name=site_name)
    building = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcBuilding", name=building_name)

    ifcopenshell.api.aggregate.assign_object(ifc, products=[site], relating_object=project)
    ifcopenshell.api.aggregate.assign_object(ifc, products=[building], relating_object=site)

    return ifc, {
        "model3d": model3d,
        "body": body,
        "axis": axis,
        "project": project,
        "site": site,
        "building": building,
    }


def add_storey(
    ifc: ifcopenshell.file,
    building,
    name: str = "Ground Floor",
    elevation: float = 0.0,
) -> object:
    """Add an IfcBuildingStorey to the building at the given elevation."""
    storey = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcBuildingStorey", name=name)
    ifcopenshell.api.aggregate.assign_object(ifc, products=[storey], relating_object=building)
    ifcopenshell.api.geometry.edit_object_placement(
        ifc,
        product=storey,
        matrix=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, elevation], [0, 0, 0, 1]],
    )
    return storey
```

### 6.2 Primitives: walls (`building_blocks/primitives/wall.py`)

```python
"""
Two-point wall author. Supports:
  - Exterior walls (IfcWall + exterior type)
  - Interior partitions (IfcWall + interior type)
  - Material layer sets
  - Wall-to-wall connectivity via connect_wall
"""
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.spatial
import ifcopenshell.api.type
from building_blocks.psets import apply_wall_common_pset


def create_wall(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    p1: tuple[float, float],
    p2: tuple[float, float],
    elevation: float = 0.0,
    height: float = 3.0,
    thickness: float = 0.2,
    name: str = "Wall",
    wall_type=None,
    fire_rating: str | None = None,
    is_external: bool = True,
) -> object:
    """
    Create an IfcWall between two 2D points at a given storey.

    Args:
        p1, p2: (x, y) in metres. The wall runs from p1 to p2.
        elevation: Z elevation of the wall base in metres.
        height: Wall height in metres.
        thickness: Wall thickness in metres.
        wall_type: Optional IfcWallType to assign.
        fire_rating: Optional "1HR", "2HR" etc for Pset_WallCommon.
        is_external: Stored in Pset_WallCommon.IsExternal.

    Returns:
        The newly created IfcWall entity.
    """
    wall = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcWall", name=name)

    # Geometry
    ifcopenshell.api.geometry.create_2pt_wall(
        ifc,
        element=wall,
        context=contexts["body"],
        p1=p1,
        p2=p2,
        elevation=elevation,
        height=height,
        thickness=thickness,
        is_si=True,
    )

    # Spatial containment
    ifcopenshell.api.spatial.assign_container(ifc, products=[wall], relating_structure=storey)

    # Type assignment
    if wall_type is not None:
        ifcopenshell.api.type.assign_type(ifc, related_objects=[wall], relating_type=wall_type)

    # Standard Pset
    apply_wall_common_pset(
        ifc, wall,
        is_external=is_external,
        fire_rating=fire_rating,
    )

    return wall
```

### 6.3 Primitives: columns (`building_blocks/primitives/column.py`)

```python
"""
Parametric column author using IfcColumn + material profile set.
Supports rectangular, circular, and standard steel I-sections.
"""
import ifcopenshell
import ifcopenshell.api
import ifcopenshell.api.geometry
import ifcopenshell.api.material
import ifcopenshell.api.root
import ifcopenshell.api.spatial


def create_column(
    ifc: ifcopenshell.file,
    contexts: dict,
    storey,
    position: tuple[float, float],
    base_elevation: float = 0.0,
    height: float = 3.0,
    profile_type: str = "RECTANGULAR",  # "RECTANGULAR" | "CIRCULAR" | "I_SECTION"
    width: float = 0.3,    # for RECTANGULAR
    depth: float = 0.3,    # for RECTANGULAR; also depth for I_SECTION
    radius: float = 0.15,  # for CIRCULAR
    name: str = "Column",
    column_type=None,
) -> object:
    """
    Create an IfcColumn at a given (x, y) position extruded upward.

    The column is authored using add_profile_representation with an
    IfcRectangleProfileDef, IfcCircleProfileDef, or IfcIShapeProfileDef.
    """
    import numpy as np

    column = ifcopenshell.api.root.create_entity(ifc, ifc_class="IfcColumn", name=name)

    # Build the profile
    if profile_type == "RECTANGULAR":
        profile = ifc.create_entity(
            "IfcRectangleProfileDef",
            ProfileType="AREA",
            ProfileName=f"{name}_profile",
            XDim=width,
            YDim=depth,
        )
    elif profile_type == "CIRCULAR":
        profile = ifc.create_entity(
            "IfcCircleProfileDef",
            ProfileType="AREA",
            ProfileName=f"{name}_profile",
            Radius=radius,
        )
    elif profile_type == "I_SECTION":
        profile = ifc.create_entity(
            "IfcIShapeProfileDef",
            ProfileType="AREA",
            ProfileName=f"{name}_profile",
            OverallWidth=width,
            OverallDepth=depth,
            WebThickness=width * 0.05,
            FlangeThickness=depth * 0.08,
        )
    else:
        raise ValueError(f"Unknown profile_type: {profile_type}")

    # Profile representation extruded vertically
    body_rep = ifcopenshell.api.geometry.add_profile_representation(
        ifc,
        context=contexts["body"],
        profile=profile,
        depth=height,
    )
    ifcopenshell.api.geometry.assign_representation(ifc, product=column, representation=body_rep)

    # Placement at (x, y, base_elevation)
    matrix = np.eye(4)
    matrix[0][3] = position[0]
    matrix[1][3] = position[1]
    matrix[2][3] = base_elevation
    ifcopenshell.api.geometry.edit_object_placement(ifc, product=column, matrix=matrix)

    ifcopenshell.api.spatial.assign_container(ifc, products=[column], relating_structure=storey)

    if column_type is not None:
        ifcopenshell.api.type.assign_type(ifc, related_objects=[column], relating_type=column_type)

    return column
```

### 6.4 Primitives: beams (`building_blocks/primitives/beam.py`)

Follow the same pattern as `column.py`. Use `add_axis_representation` for the axis and `add_profile_representation` for the body. The beam runs from `p1` to `p2` at a given elevation. The axis direction determines the extrusion direction. Implement `create_beam(ifc, contexts, storey, p1, p2, elevation, profile_type, width, depth, name, beam_type)`.

### 6.5 Primitives: slabs (`building_blocks/primitives/slab.py`)

Use `ifcopenshell.api.geometry.add_slab_representation` with a `polyline` argument for non-rectangular slabs. Implement `create_slab(ifc, contexts, storey, boundary_points, depth, elevation, name, slab_type)`. The `boundary_points` is a list of `(x, y)` tuples defining the slab outline.

### 6.6 Primitives: doors and windows

Use `ifcopenshell.api.geometry.add_door_representation` and `add_window_representation` which natively generate parametric door/window geometry including lining and panel properties. Use `ifcopenshell.api.feature.add_feature` to cut the host wall opening correctly. Implement:

- `create_door(ifc, contexts, storey, host_wall, distance_along_wall, sill_height, width, height, operation_type, name)`
- `create_window(ifc, contexts, storey, host_wall, distance_along_wall, sill_height, width, height, partition_type, name)`

Both should call `add_feature` to create the semantic void in the host wall, then fill it with the door/window element.

### 6.7 Primitives: stairs, railings, roofs

- **Stairs**: `IfcStairFlight` authored via `add_profile_representation` for treads. Implement `create_stair(ifc, contexts, storey, start_point, width, num_risers, riser_height, tread_depth, name)`.
- **Railings**: Use `ifcopenshell.api.geometry.add_railing_representation` which takes a `railing_path` and supports `WALL_MOUNTED_HANDRAIL` type. Implement `create_railing(ifc, contexts, storey, path_points, height, railing_diameter, name)`.
- **Flat roofs**: `IfcRoof` with `add_slab_representation` for body. Implement `create_flat_roof(ifc, contexts, storey, boundary_points, thickness, name)`.
- **Pitched roofs**: `IfcRoof` with `add_mesh_representation` for arbitrary ridge geometry. Implement `create_pitched_roof(ifc, contexts, storey, boundary_points, ridge_height, name)`.

### 6.8 Type library (`building_blocks/types/`)

Each type module defines reusable `IfcXxxType` entities with material layer sets or profile sets. Example for `wall_types.py`:

```python
"""
Pre-defined IfcWallType definitions with material layer sets.
These are registered once per IFC file and shared by all wall occurrences.
"""
import ifcopenshell
import ifcopenshell.api


def create_exterior_wall_type(
    ifc: ifcopenshell.file,
    name: str = "EXT-WALL-200",
    outer_finish_thickness: float = 0.012,   # plasterboard
    insulation_thickness: float = 0.1,
    structural_thickness: float = 0.2,       # concrete
    inner_finish_thickness: float = 0.012,
) -> object:
    """
    Creates an IfcWallType with a 4-layer material set:
    plasterboard / insulation / structural / plasterboard.
    """
    wall_type = ifcopenshell.api.root.create_entity(
        ifc, ifc_class="IfcWallType", name=name, predefined_type="STANDARD",
    )

    material_set = ifcopenshell.api.material.add_material_set(
        ifc, name=name, set_type="IfcMaterialLayerSet",
    )

    layers_spec = [
        ("PB01", "gypsum",     inner_finish_thickness),
        ("INS01", "concrete",  insulation_thickness),
        ("CON01", "concrete",  structural_thickness),
        ("PB01", "gypsum",     outer_finish_thickness),
    ]

    for mat_name, category, thickness in layers_spec:
        mat = ifcopenshell.api.material.add_material(ifc, name=mat_name, category=category)
        layer = ifcopenshell.api.material.add_layer(ifc, layer_set=material_set, material=mat)
        ifcopenshell.api.material.edit_layer(
            ifc, layer=layer, attributes={"LayerThickness": thickness},
        )

    ifcopenshell.api.material.assign_material(ifc, products=[wall_type], material=material_set)

    # Pset_WallCommon
    pset = ifcopenshell.api.pset.add_pset(ifc, product=wall_type, name="Pset_WallCommon")
    ifcopenshell.api.pset.edit_pset(
        ifc, pset=pset,
        properties={"IsExternal": True, "LoadBearing": True},
    )

    return wall_type
```

Follow the same pattern for `IfcColumnType` (with `IfcMaterialProfileSet`) and `IfcBeamType`.

### 6.9 Property sets helper (`building_blocks/psets.py`)

```python
"""
Convenience wrappers for the most commonly needed standard property sets.
All pset names and property names follow buildingSMART convention.
Consult bSDD for the full catalogue.
"""
import ifcopenshell.api


def apply_wall_common_pset(
    ifc, wall,
    is_external: bool = True,
    fire_rating: str | None = None,
    acoustic_rating: str | None = None,
    thermal_transmittance: float | None = None,
):
    """Apply Pset_WallCommon to a wall or wall type."""
    pset = ifcopenshell.api.pset.add_pset(ifc, product=wall, name="Pset_WallCommon")
    props = {"IsExternal": is_external}
    if fire_rating:
        props["FireRating"] = fire_rating
    if acoustic_rating:
        props["AcousticRating"] = acoustic_rating
    if thermal_transmittance is not None:
        props["ThermalTransmittance"] = thermal_transmittance
    ifcopenshell.api.pset.edit_pset(ifc, pset=pset, properties=props)


def apply_door_common_pset(
    ifc, door,
    fire_rating: str | None = None,
    is_external: bool = False,
    security_rating: str | None = None,
):
    """Apply Pset_DoorCommon."""
    pset = ifcopenshell.api.pset.add_pset(ifc, product=door, name="Pset_DoorCommon")
    props = {"IsExternal": is_external}
    if fire_rating:
        props["FireRating"] = fire_rating
    if security_rating:
        props["SecurityRating"] = security_rating
    ifcopenshell.api.pset.edit_pset(ifc, pset=pset, properties=props)


def apply_space_common_pset(
    ifc, space,
    reference: str | None = None,
    category: str | None = None,
):
    """Apply Pset_SpaceCommon."""
    pset = ifcopenshell.api.pset.add_pset(ifc, product=space, name="Pset_SpaceCommon")
    props = {}
    if reference:
        props["Reference"] = reference
    if category:
        props["Category"] = category
    ifcopenshell.api.pset.edit_pset(ifc, pset=pset, properties=props)
```

### 6.10 bSDD client (`building_blocks/bsdd.py`)

```python
"""
Lightweight async client for the buildingSMART Data Dictionary REST API.

Reference: https://technical.buildingsmart.org/services/bsdd/using-the-bsdd-api/
Base URL: https://api.bsdd.buildingsmart.org

Key endpoints used:
  GET /api/Class/v1  → class details + standard properties
  GET /api/SearchList/v1 → fuzzy search for classes

Usage:
  props = await get_class_properties("IfcWall", dictionary_uri="https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3")
"""
import httpx
from typing import Optional

BSDD_BASE = "https://api.bsdd.buildingsmart.org"
IFC_DICT_URI = "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3"


async def search_classes(query: str, dictionary_uri: str = IFC_DICT_URI) -> list[dict]:
    """Search bSDD for classes matching a text query."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{BSDD_BASE}/api/SearchList/v1",
            params={
                "SearchText": query,
                "DictionaryUri": dictionary_uri,
                "languageCode": "en-GB",
            },
            headers={"User-Agent": "ifc-gpt-v2/2.0"},
            timeout=10.0,
        )
        r.raise_for_status()
        return r.json().get("Classes", [])


async def get_class_properties(
    class_uri: str,
    include_child_class_properties: bool = False,
) -> dict:
    """
    Retrieve full class details and its standard properties from bSDD.
    class_uri example: "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall"
    """
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{BSDD_BASE}/api/Class/v1",
            params={
                "uri": class_uri,
                "includeChildClassProperties": include_child_class_properties,
                "languageCode": "en-GB",
            },
            headers={"User-Agent": "ifc-gpt-v2/2.0"},
            timeout=10.0,
        )
        r.raise_for_status()
        return r.json()


async def get_pset_properties_for_element(ifc_class_name: str) -> list[dict]:
    """
    Convenience: given an IFC class name like 'IfcWall', return
    the standard properties from bSDD as a flat list.
    Useful for building prompt context for the LLM.
    """
    uri = f"{IFC_DICT_URI}/class/{ifc_class_name}"
    data = await get_class_properties(uri)
    return data.get("ClassProperties", [])
```

### 6.11 Validation runner (`validation/runner.py`)

```python
"""
Wraps ifctester to validate an IFC file against one or more IDS files.
Returns a structured dict with pass/fail counts and per-requirement detail.
"""
from pathlib import Path
import ifctester
import ifctester.reporter


def validate(ifc_path: str | Path, ids_paths: list[str | Path]) -> dict:
    """
    Validate the IFC file against each IDS specification.

    Returns:
        {
            "passed": bool,
            "total": int,
            "failed": int,
            "results": [{"ids_file": str, "report": {...}}]
        }
    """
    ifc_path = Path(ifc_path)
    results = []
    total = 0
    failed = 0

    for ids_path in ids_paths:
        ids_path = Path(ids_path)
        ids = ifctester.open(str(ids_path))
        ids.validate(str(ifc_path))
        reporter = ifctester.reporter.Json(ids)
        reporter.report()
        report = reporter.to_string()
        for spec in ids.specifications:
            total += 1
            if not spec.status:
                failed += 1
        results.append({"ids_file": ids_path.name, "report": report})

    return {
        "passed": failed == 0,
        "total": total,
        "failed": failed,
        "results": results,
    }
```

---

## 7. Phase 2 — FastAPI Server

### 7.1 App factory (`api/server.py`)

```python
"""FastAPI application factory for IFC-GPT v2."""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse  # noqa: imported for re-export

load_dotenv()

WORKSPACE = Path(os.getenv("WORKSPACE_DIR", "./workspace"))
WORKSPACE.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield  # Add startup / shutdown logic here (e.g., warm up LLM)


app = FastAPI(title="IFC-GPT v2", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        os.getenv("FRONTEND_ORIGIN", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/workspace", StaticFiles(directory=str(WORKSPACE)), name="workspace")

# Register routes
from api.routes import generate, build_from_plan, modify, voice, status  # noqa: E402

app.include_router(generate.router, prefix="/api")
app.include_router(build_from_plan.router, prefix="/api")
app.include_router(modify.router, prefix="/api")
app.include_router(voice.router, prefix="/api")
app.include_router(status.router, prefix="/api")


def main():
    import sys, uvicorn
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 8000
    uvicorn.run("api.server:app", host="0.0.0.0", port=port, reload=True)
```

### 7.2 Job store (`api/deps.py`)

```python
"""
Simple in-memory job store (replace with Supabase jobs table in production).
Also provides Supabase JWT verification dependency.
"""
import os
from typing import Any
from jose import jwt, JWTError
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_jobs: dict[str, dict[str, Any]] = {}

def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)

def set_job(job_id: str, data: dict):
    _jobs[job_id] = data

def update_job(job_id: str, patch: dict):
    if job_id in _jobs:
        _jobs[job_id].update(patch)

# --- JWT verification (Supabase) ---
security = HTTPBearer(auto_error=False)

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Optional auth: returns user_id if token valid, None otherwise."""
    if credentials is None:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            os.getenv("SUPABASE_JWT_SECRET", ""),
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### 7.3 SSE status stream (`api/routes/status.py`)

```python
import asyncio
import json
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from api.deps import get_job

router = APIRouter()

@router.get("/status/{job_id}/stream")
async def stream_status(job_id: str):
    async def generator():
        while True:
            job = get_job(job_id) or {"status": "not_found"}
            yield {"data": json.dumps(job)}
            if job.get("status") in ("complete", "error", "not_found"):
                break
            await asyncio.sleep(1.5)
    return EventSourceResponse(generator())

@router.get("/status/{job_id}")
async def get_status(job_id: str):
    job = get_job(job_id)
    if not job:
        return {"status": "not_found", "job_id": job_id}
    return {"job_id": job_id, **job}
```

### 7.4 Generate route (`api/routes/generate.py`)

```python
import asyncio
import uuid
from fastapi import APIRouter
from pydantic import BaseModel
from api.deps import set_job, update_job

router = APIRouter()

class GenerateRequest(BaseModel):
    message: str

@router.post("/generate")
async def generate(req: GenerateRequest):
    job_id = str(uuid.uuid4())[:8]
    set_job(job_id, {"status": "queued", "ifc_url": None, "error": None})
    asyncio.create_task(_run(job_id, req.message))
    return {"job_id": job_id, "status": "queued"}

async def _run(job_id: str, message: str):
    update_job(job_id, {"status": "running"})
    try:
        from agent.graph import run_pipeline
        loop = asyncio.get_event_loop()
        state = await loop.run_in_executor(None, lambda: run_pipeline(message))
        ifc_path = state.get("final_ifc_path", "")
        from pathlib import Path
        ifc_url = f"/workspace/{Path(ifc_path).name}" if ifc_path and Path(ifc_path).exists() else None
        update_job(job_id, {"status": "complete", "ifc_url": ifc_url, "error": None})
    except Exception as e:
        update_job(job_id, {"status": "error", "ifc_url": None, "error": str(e)})
```

Implement `build_from_plan.py`, `modify.py`, and `voice.py` following the same pattern as `generate.py`. The `voice.py` route accepts an audio `UploadFile`, calls the OpenAI Whisper API, and then dispatches `_run(job_id, transcript)`.

---

## 8. Phase 3 — LangGraph Agent Pipeline

### 8.1 Expanded `BuildingPlan` schema (`agent/schemas.py`)

```python
"""
Expanded BuildingPlan for v2. All elements map 1:1 to building_blocks functions.
"""
from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class StoreyDefinition(BaseModel):
    storey_ref: str
    name: str
    elevation: float = 0.0
    floor_to_floor_height: float = 3.0


class WallPlacement(BaseModel):
    element_type: Literal["wall"] = "wall"
    wall_ref: str
    component_id: str = "exterior_wall"
    storey_ref: str
    start_point: tuple[float, float]
    end_point: tuple[float, float]
    height: float = 3.0
    thickness: float = 0.2
    fire_rating: Optional[str] = None
    is_external: bool = True
    wall_type_ref: Optional[str] = None


class ColumnPlacement(BaseModel):
    element_type: Literal["column"] = "column"
    column_ref: str
    storey_ref: str
    position: tuple[float, float]
    base_elevation: float = 0.0
    height: float = 3.0
    profile_type: Literal["RECTANGULAR", "CIRCULAR", "I_SECTION"] = "RECTANGULAR"
    width: float = 0.3
    depth: float = 0.3
    radius: float = 0.15
    column_type_ref: Optional[str] = None


class BeamPlacement(BaseModel):
    element_type: Literal["beam"] = "beam"
    beam_ref: str
    storey_ref: str
    start_point: tuple[float, float]
    end_point: tuple[float, float]
    elevation: float = 3.0
    profile_type: Literal["RECTANGULAR", "I_SECTION"] = "I_SECTION"
    width: float = 0.2
    depth: float = 0.4
    beam_type_ref: Optional[str] = None


class SlabPlacement(BaseModel):
    element_type: Literal["slab"] = "slab"
    storey_ref: str
    boundary_points: list[tuple[float, float]]
    depth: float = 0.2
    elevation: float = 0.0
    slab_type: Literal["FLOOR", "ROOF", "LANDING"] = "FLOOR"


class OpeningPlacement(BaseModel):
    element_type: Literal["door", "window"]
    storey_ref: str
    host_wall_ref: str
    distance_along_wall: float
    sill_height: float = 0.0
    width: float = 0.9
    height: float = 2.1
    operation_type: Optional[str] = None    # for doors: SINGLE_SWING_LEFT, etc.
    partition_type: Optional[str] = None   # for windows: SINGLE_PANEL, etc.
    fire_rating: Optional[str] = None


class RoofPlacement(BaseModel):
    element_type: Literal["roof"] = "roof"
    storey_ref: str
    boundary_points: list[tuple[float, float]]
    roof_type: Literal["FLAT", "GABLE", "HIP"] = "FLAT"
    ridge_height: float = 1.5
    thickness: float = 0.25


class StairPlacement(BaseModel):
    element_type: Literal["stair"] = "stair"
    storey_ref: str
    start_point: tuple[float, float]
    direction: tuple[float, float] = (1.0, 0.0)
    width: float = 1.2
    num_risers: int = 18
    riser_height: float = 0.175
    tread_depth: float = 0.25


class RailingPlacement(BaseModel):
    element_type: Literal["railing"] = "railing"
    storey_ref: str
    path_points: list[tuple[float, float, float]]
    height: float = 1.0
    railing_diameter: float = 0.05


ElementPlacement = (
    WallPlacement | ColumnPlacement | BeamPlacement | SlabPlacement |
    OpeningPlacement | RoofPlacement | StairPlacement | RailingPlacement
)


class TypeDefinition(BaseModel):
    """Pre-defined IfcXxxType to register before placing occurrences."""
    type_ref: str
    ifc_class: str     # "IfcWallType", "IfcColumnType", etc.
    preset: Optional[str] = None   # e.g. "exterior_wall_200", "concrete_column_300x300"
    custom_params: dict[str, Any] = Field(default_factory=dict)


class BuildingPlan(BaseModel):
    description: str
    site: dict = Field(default_factory=lambda: {"name": "Default Site"})
    building: dict = Field(default_factory=lambda: {"name": "Building A", "building_type": "Mixed-use"})
    storeys: list[StoreyDefinition]
    types: list[TypeDefinition] = Field(default_factory=list)
    elements: list[ElementPlacement]
    wall_junctions: list[dict] = Field(default_factory=list)
    rooms: list[dict] = Field(default_factory=list)
```

### 8.2 Build node (`agent/nodes/build.py`)

The build node receives a `BuildingPlan` and calls `building_blocks` functions. Its core logic is:

1. Call `building_blocks.context.create_ifc_project()` to set up the IFC file.
2. For each storey in `plan.storeys`, call `add_storey()`.
3. For each type in `plan.types`, call the appropriate type factory from `building_blocks/types/`.
4. For each element in `plan.elements`, dispatch to the correct primitive function.
5. Save the IFC file to `workspace/{job_id}.ifc`.
6. Return the file path as `state["final_ifc_path"]`.

The build node must handle wall-to-wall connectivity: after all walls are placed, call `ifcopenshell.api.geometry.connect_wall` for adjacent walls that share a common endpoint.

### 8.3 LLM (`agent/llm.py`)

Keep the existing `AzureResponsesChatModel` wrapper but update the default model name to `gpt-5.4-pro` everywhere:

```python
azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4-pro")
# ...
kwargs: dict = {"temperature": temperature, "model": "gpt-5.4-pro"}
```

Also add a note in the docstring:

```python
"""
LLM client factory. Default model: gpt-5.4-pro.

If AZURE_OPENAI_API_KEY is set, uses the Azure Responses API.
If gpt-5.4-pro supports Chat Completions on your Azure resource,
replace AzureResponsesChatModel with AzureChatOpenAI from langchain_openai.
"""
```

---

## 9. Phase 4 — Next.js 15 Frontend

### 9.1 Bootstrap

```bash
npx create-next-app@latest web/ \
  --typescript --tailwind --eslint --app \
  --no-src-dir --import-alias "@/*"
cd web
npm install @thatopen/components @thatopen/components-front three @types/three
npm install framer-motion zustand
npm install @supabase/supabase-js
```

### 9.2 shadcn/ui setup (critical for beautiful UI in Windsurf)

shadcn/ui has an official MCP server for Windsurf that allows AI to generate correct components directly.[cite:118][cite:127]

**Add the shadcn MCP to Windsurf:**

In Windsurf's MCP configuration (`.windsurf/mcp.json`):

```json
{
  "mcpServers": {
    "shadcn": {
      "command": "npx",
      "args": ["-y", "shadcn@canary", "registry", "mcp"]
    }
  }
}
```

This enables Windsurf to call `shadcn/ui` component documentation and code generation directly, producing correct component code for the current shadcn version.[cite:118]

**Install shadcn CLI and initialize:**

```bash
cd web
npx shadcn@latest init
```

Choose: Dark theme, CSS variables, Tailwind. Then install the components needed:

```bash
npx shadcn@latest add button input textarea badge card separator tabs
npx shadcn@latest add scroll-area dialog sheet tooltip progress
```

### 9.3 Design system

Set up a BIM-dark design system in `web/tailwind.config.ts`:

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // BIM dark palette
        canvas:   "hsl(230, 15%, 8%)",   // main 3D canvas background
        panel:    "hsl(225, 12%, 11%)",  // left/right panel background
        surface:  "hsl(225, 10%, 15%)",  // cards, inputs
        border:   "hsl(225, 10%, 22%)",  // subtle borders
        accent:   "hsl(262, 80%, 65%)",  // purple — primary actions
        success:  "hsl(142, 70%, 45%)",  // job complete
        warning:  "hsl(45,  95%, 55%)",  // job running
        danger:   "hsl(0,   75%, 55%)",  // job error
        muted:    "hsl(225, 10%, 45%)",  // secondary text
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui"],
        mono: ["var(--font-geist-mono)", "monospace"],
      },
      animation: {
        "pulse-fast": "pulse 1s ease-in-out infinite",
        "fade-in":    "fadeIn 0.3s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%":   { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
```

### 9.4 Root layout (`web/app/layout.tsx`)

```tsx
import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";

export const metadata: Metadata = {
  title: "IFC-GPT v2",
  description: "AI-powered BIM generation",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${GeistSans.variable} ${GeistMono.variable} bg-canvas text-white antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
```

Install Geist fonts: `npm install geist`

### 9.5 App shell (`web/components/AppShell.tsx`)

Use a two-panel layout with Framer Motion for panel transitions:

```tsx
"use client";
import { motion } from "framer-motion";

export default function AppShell({
  leftPanel,
  rightPanel,
}: {
  leftPanel: React.ReactNode;
  rightPanel: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden bg-canvas">
      {/* Left control panel */}
      <motion.aside
        initial={{ x: -20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="w-[380px] shrink-0 flex flex-col border-r border-border bg-panel overflow-y-auto"
      >
        {leftPanel}
      </motion.aside>

      {/* Right 3D canvas */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="flex-1 relative overflow-hidden"
      >
        {rightPanel}
      </motion.div>
    </div>
  );
}
```

### 9.6 IFC Viewer (`web/components/IFCViewer.tsx`)

Load ThatOpen IFC viewer client-side with `dynamic` import since it requires browser APIs.[cite:138] The viewer receives the IFC URL and calls back with selected element GUIDs for the modify panel.[cite:138]

```tsx
"use client";
import { useEffect, useRef } from "react";

interface Props {
  ifcUrl: string | null;
  onElementSelected?: (guids: string[]) => void;
}

export default function IFCViewer({ ifcUrl, onElementSelected }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const disposeRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!containerRef.current || !ifcUrl) return;
    let cancelled = false;

    (async () => {
      const OBC  = await import("@thatopen/components");
      const OBCF = await import("@thatopen/components-front");

      const components = new OBC.Components();
      const worlds     = components.get(OBC.Worlds);
      const world      = worlds.create<
        OBC.SimpleScene,
        OBC.SimpleRenderer,
        OBC.SimpleCamera
      >();

      world.scene    = new OBC.SimpleScene(components);
      world.renderer = new OBC.SimpleRenderer(components, containerRef.current!);
      world.camera   = new OBC.SimpleCamera(components);
      (world.scene as any).setup?.();
      components.init();

      // Load IFC
      const loader = components.get(OBC.IfcLoader);
      await loader.setup();
      const res    = await fetch(ifcUrl);
      const buf    = await res.arrayBuffer();
      const model  = await loader.load(new Uint8Array(buf));

      // Fit camera
      const bbox   = components.get(OBC.BoundingBoxer);
      bbox.add(model);
      const sphere = bbox.getSphere();
      (world.camera as any).controls?.fitToSphere(sphere, true);
      bbox.reset();

      // Highlighter → GUID extraction
      if (onElementSelected && !cancelled) {
        const highlighter = components.get(OBCF.Highlighter);
        highlighter.setup({ world });
        highlighter.events.select.onHighlight.add((fragmentIdMap: Record<string, Set<number>>) => {
          const frags  = components.get(OBC.FragmentsManager);
          const guids: string[] = [];
          for (const [fragId, ids] of Object.entries(fragmentIdMap)) {
            const frag = frags.list.get(fragId);
            if (!frag) continue;
            for (const id of ids) {
              const guid = (frag as any).getItemGuid?.(id);
              if (guid) guids.push(guid);
            }
          }
          onElementSelected(guids);
        });
        highlighter.events.select.onClear.add(() => onElementSelected([]));
      }

      disposeRef.current = () => { try { components.dispose(); } catch {} };
    })();

    return () => {
      cancelled = true;
      disposeRef.current?.();
    };
  }, [ifcUrl]);

  return (
    <div
      ref={containerRef}
      className="w-full h-full bg-canvas"
      style={{ minHeight: "100%" }}
    />
  );
}
```

### 9.7 Main page (`web/app/page.tsx`)

Structure the main page around:

1. `AppShell` wrapper
2. Left panel contains:
   - IFC-GPT logo / title badge (powered by gpt-5.4-pro)
   - Mode switcher tabs: **Text / Voice | Draw**
   - Text input + voice record button
   - Job status badge (SSE-connected via `useJob` hook)
   - Modify panel (appears when a GUID is selected)
3. Right panel: `IFCViewer` (dynamic import)

Use `shadcn/ui` `Tabs`, `Textarea`, `Button`, `Badge`, `Card`, and `Separator` components throughout.

### 9.8 Job status hook (`web/hooks/useJob.ts`)

```typescript
"use client";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type JobStatus = "idle" | "queued" | "running" | "complete" | "error";

export interface Job {
  job_id: string;
  status: JobStatus;
  ifc_url: string | null;
  error: string | null;
}

export function useJob() {
  const [job, setJob] = useState<Job | null>(null);

  const dispatch = async (endpoint: string, body: object): Promise<string> => {
    const res  = await fetch(`${API}/api/${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    setJob({ ...data, ifc_url: null });
    return data.job_id;
  };

  useEffect(() => {
    if (!job?.job_id || job.status === "complete" || job.status === "error") return;
    const es = new EventSource(`${API}/api/status/${job.job_id}/stream`);
    es.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setJob((prev) => ({ ...prev!, ...data }));
      if (data.status === "complete" || data.status === "error") es.close();
    };
    return () => es.close();
  }, [job?.job_id]);

  return { job, dispatch, setJob };
}
```

### 9.9 `next.config.ts`

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  webpack: (config) => {
    config.experiments = { ...config.experiments, asyncWebAssembly: true };
    return config;
  },
};

export default nextConfig;
```

### 9.10 `web/.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://<project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

---

## 10. Phase 5 — Supabase Integration

### 10.1 Database schema

Run in Supabase SQL editor:

```sql
-- Projects table
CREATE TABLE projects (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  name        TEXT NOT NULL DEFAULT 'Untitled',
  description TEXT,
  ifc_path    TEXT,
  created_at  TIMESTAMPTZ DEFAULT now(),
  updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Job history
CREATE TABLE jobs (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     UUID REFERENCES auth.users(id),
  project_id  UUID REFERENCES projects(id),
  status      TEXT NOT NULL DEFAULT 'queued',
  message     TEXT,
  ifc_url     TEXT,
  error       TEXT,
  created_at  TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ
);

-- Row-level security
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs     ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own projects"
  ON projects USING (auth.uid() = user_id);

CREATE POLICY "Users can view own jobs"
  ON jobs USING (auth.uid() = user_id);
```

### 10.2 FastAPI JWT middleware

The `verify_token` dependency in `api/deps.py` (already defined above) verifies Supabase JWTs using `SUPABASE_JWT_SECRET`. Apply it to authenticated routes by adding `user_id: str = Depends(verify_token)` to any endpoint that requires auth.[cite:148][cite:151]

### 10.3 IFC file storage

In production, upload generated IFC files to Supabase Storage instead of local `workspace/`:

```python
from supabase import create_client

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
)

def upload_ifc(local_path: str, job_id: str) -> str:
    """Upload IFC file to Supabase Storage. Returns public URL."""
    with open(local_path, "rb") as f:
        bucket = supabase.storage.from_("ifc-files")
        bucket.upload(f"jobs/{job_id}.ifc", f, {"content-type": "application/x-step"})
        return bucket.get_public_url(f"jobs/{job_id}.ifc")
```

---

## 11. Phase 6 — Voice Input

Voice input is already wired via the `/api/voice` endpoint and `useVoice.ts` hook. Ensure:

1. `web/hooks/useVoice.ts` uses `MediaRecorder` with `audio/webm` MIME type.
2. The audio blob is posted as `multipart/form-data` with field name `audio`.
3. `api/routes/voice.py` reads the file, writes to `/tmp`, calls `openai.audio.transcriptions.create(model="whisper-1")`, then dispatches `generate` with the transcript.
4. Transcript is echoed back in the job status response so the frontend can pre-fill the text area.

---

## 12. AGENTS.md (Place in Repo Root)

Create `AGENTS.md` at the project root — this is the AI coding agent configuration file that improves Windsurf's output quality for this specific project:[cite:162][cite:165]

```markdown
# AGENTS.md — IFC-GPT v2

## Project summary
A from-scratch BIM-AI web application. Python FastAPI backend + Next.js 15 frontend.
Generates IFC4 files natively using IfcOpenShell. No Blender or Bonsai.

## Key conventions

### Python
- Use `uv` for package management. Never use `pip install` directly.
- All IFC authoring goes through `building_blocks/`. Never call `ifcopenshell` directly from `agent/` or `api/`.
- LangGraph nodes live in `agent/nodes/`. Each is a pure function: `state → state`.
- Model: `gpt-5.4-pro`. Never hardcode any other model name.
- Type hints required on all public functions.
- Use `from __future__ import annotations` in all Python files.

### TypeScript / Next.js
- All components are in `web/components/`.
- ThatOpen viewer is client-only. Always use `dynamic(() => import(...), { ssr: false })`.
- Never call the FastAPI backend directly from server components. Use client hooks.
- Use `shadcn/ui` components for all UI primitives. Do not build custom button/input/card from scratch.
- Tailwind only. No inline styles except for canvas containers.
- Framer Motion for all transitions and animations.

### IFC authoring rules
- All elements must be assigned to a storey via `ifcopenshell.api.spatial.assign_container`.
- All elements should have a property set (`Pset_*Common`) via `building_blocks/psets.py`.
- Always use types (`IfcWallType`, `IfcColumnType`, etc.) for repeated elements.
- Openings in walls for doors/windows must use `ifcopenshell.api.feature.add_feature`.
- Wall connectivity must use `ifcopenshell.api.geometry.connect_wall`.

### Testing
- Every `building_blocks/primitives/*.py` function must have a corresponding test in `tests/`.
- Tests create an IFC file, call the function, validate the IFC parses cleanly.
- Run: `uv run pytest tests/ -v`

### Do not
- Do not start Blender or import bonsai.
- Do not add MCP server code to the main runtime.
- Do not use `ifcopenshell.api.run()` — it is deprecated. Call API functions directly.
- Do not commit `.ifc` files to git.
```

---

## 13. Full Startup Commands

### Development (two terminals)

```bash
# Terminal 1 — Python backend
uv run main.py

# Terminal 2 — Next.js frontend
cd web && npm run dev
```

### Production

```bash
# Build frontend
cd web && npm run build

# Start both
uv run main.py --port 8000 &
cd web && npm run start
```

---

## 14. Build Checklist for Windsurf

Work through this list in order:

- [ ] **Phase 0:** pyproject.toml, .env.example, main.py
- [ ] **Phase 1:** `building_blocks/context.py`
- [ ] **Phase 1:** `building_blocks/primitives/wall.py`
- [ ] **Phase 1:** `building_blocks/primitives/column.py`
- [ ] **Phase 1:** `building_blocks/primitives/beam.py`
- [ ] **Phase 1:** `building_blocks/primitives/slab.py`
- [ ] **Phase 1:** `building_blocks/primitives/door.py`
- [ ] **Phase 1:** `building_blocks/primitives/window.py`
- [ ] **Phase 1:** `building_blocks/primitives/roof.py`
- [ ] **Phase 1:** `building_blocks/primitives/stair.py`
- [ ] **Phase 1:** `building_blocks/primitives/railing.py`
- [ ] **Phase 1:** `building_blocks/primitives/footing.py`
- [ ] **Phase 1:** `building_blocks/primitives/member.py`
- [ ] **Phase 1:** `building_blocks/primitives/curtain_wall.py`
- [ ] **Phase 1:** `building_blocks/types/wall_types.py`
- [ ] **Phase 1:** `building_blocks/types/column_types.py`
- [ ] **Phase 1:** `building_blocks/types/beam_types.py`
- [ ] **Phase 1:** `building_blocks/types/door_types.py`
- [ ] **Phase 1:** `building_blocks/types/window_types.py`
- [ ] **Phase 1:** `building_blocks/psets.py`
- [ ] **Phase 1:** `building_blocks/bsdd.py`
- [ ] **Phase 1:** `validation/runner.py`
- [ ] **Phase 1:** Pytest for each primitive
- [ ] **Phase 2:** `api/server.py`, `api/deps.py`
- [ ] **Phase 2:** All `api/routes/` modules
- [ ] **Phase 3:** `agent/schemas.py`
- [ ] **Phase 3:** `agent/llm.py` (gpt-5.4-pro)
- [ ] **Phase 3:** All `agent/nodes/` modules
- [ ] **Phase 3:** `agent/graph.py`
- [ ] **Phase 4:** Next.js bootstrap, shadcn MCP config
- [ ] **Phase 4:** `web/tailwind.config.ts` design system
- [ ] **Phase 4:** `web/components/IFCViewer.tsx`
- [ ] **Phase 4:** `web/components/AppShell.tsx`
- [ ] **Phase 4:** `web/components/ChatPanel.tsx`
- [ ] **Phase 4:** `web/hooks/useJob.ts`
- [ ] **Phase 4:** `web/hooks/useVoice.ts`
- [ ] **Phase 4:** `web/app/page.tsx`
- [ ] **Phase 5:** Supabase SQL schema
- [ ] **Phase 5:** `api/deps.py` JWT verification
- [ ] **Phase 6:** `api/routes/voice.py`
- [ ] **Phase 6:** `web/hooks/useVoice.ts`

---

## 15. FloorPlan2IFC Pipeline (Implemented Mar 27 2026)

This phase upgrades the floor plan ingestion pipeline from a pure-OpenCV placeholder into a production-grade two-branch detection system, adds a MiC (Modular integrated Construction) room dimension catalog, and implements a user-confirmation API workflow.

### 15.1 What was built

| Component | Location | Purpose |
|---|---|---|
| VLM detection branch | `floorplan/detect.py` | Calls `gpt-5.4-pro` vision API with structured JSON output to detect walls, doors, windows, rooms, and columns from floor plan images |
| VLM prompt files | `floorplan/prompts/detect_system.txt`, `detect_user.txt` | Architectural floor plan analysis prompts |
| VLM/CV merge | `floorplan/detect.py` `_merge_vlm_cv_walls()` | Snaps VLM wall endpoints to nearest OpenCV-detected line within 10px tolerance |
| MiC room catalog | `building_blocks/mic_catalog.py` | 19 module types with dimensions derived from 49 real Hong Kong MiC IFC modules. Maps room labels → categories, provides typical dimensions and expected opening counts |
| Room classification | `floorplan/plan_builder.py` | Rooms enriched with MiC category, expected doors/windows, typical dimensions |
| Confirmation workflow | `api/routes/floorplan.py` | `POST /upload` → `GET /plan` → `POST /confirm` with state machine: detecting → awaiting_confirmation → building → complete |

### 15.2 Pain points addressed

From `workspace/floorplan_learnings.json`:

| Pain Point | Fix |
|---|---|
| VLM detection was a no-op placeholder | Real VLM branch calling `gpt-5.4-pro` with structured JSON schema, exponential backoff, image clamping to 4096px |
| No room type classification | VLM prompts detect rooms with proper labels; MiC catalog classifies into standard categories |
| No door/window detection from images | VLM branch detects openings with position, width, and host wall assignment |
| Template-based room layouts (55%/28% splits) | MiC catalog provides real residential dimensions from HK MiC standards |
| No user review before IFC build | Confirmation API: detection results are exposed for review/edit before triggering build |

### 15.3 Guardrails implemented

Per `new shit/GUARDRAILS.md`:

- **G-01**: File type + size validation (PDF ≤50MB, images ≤25MB)
- **G-15**: Images clamped to 4096px before VLM (cost control)
- **G-17**: VLM calls wrapped with 3-retry exponential backoff (2s/4s/8s)
- **G-23**: All background task exceptions caught, logged, stored in job error
- **G-24**: Strict state machine: detecting → awaiting_confirmation → building → complete | error

### 15.4 MiC module catalog

Derived from analysis of 49 individual MiC IFC files extracted from `HSK_HSK1A_GVDC_ALL_IFC4x3.ifc` (a real Hong Kong MiC housing project). Module types:

| Code | Room Type | Typical Size (W×D m) |
|---|---|---|
| TYPE 1.x (MB) | Master Bedroom | 3.5×4.0 – 3.8×4.5 |
| TYPE 2.x (BT) | Bathroom | 1.8×2.4 – 2.4×3.2 |
| TYPE 3.x (LK/LD) | Living/Kitchen, Living/Dining | 3.5×5.5 – 3.8×7.0 |
| TYPE 4.x (KT) | Kitchen | 2.5×3.5 – 2.8×4.0 |
| TYPE 5.x (BR) | Bedroom (secondary) | 2.8×3.5 – 3.0×3.8 |
| TYPE 6 (TL) | Toilet | 1.2×1.8 |
| TYPE 7/9 (EMR) | E&M Room | 2.0×2.5 |
| TYPE 8 (RMSRR) | Refuse/Service | 2.0×2.5 |
| TYPE 10 (WMC) | Water Meter Closet | 1.0×1.5 |

### 15.5 Build experiment results

5-storey L-shaped mixed-use building (30×12m main + 12×18m wing):

| Metric | Value |
|---|---|
| Total IFC products | 543 |
| Walls | 70 (all with geometry) |
| Windows | 105 (all fill openings) |
| Columns | 105 (mix of rectangular + circular) |
| Beams | 80 (mix of steel I-section + concrete rectangular) |
| Doors | 25 (all fill openings) |
| Slabs + Stairs + Railings + Elevators + Roof | 21 |
| Build time | 1.4 seconds |
| File size | 891 KB |
| Orphaned elements | 0 |

### 15.6 Test count

222 tests passing (was 187). New tests:
- `tests/test_mic_catalog.py` — 27 tests for room classification, dimensions, opening defaults, catalog integrity
- `tests/test_floorplan.py` — 8 new tests for VLM helpers (`_clamp_image_for_vlm`, `_merge_vlm_cv_walls`, VLM fallback) and MiC-enriched plan_builder

---

## 16. Known Constraints

| Constraint | Detail |
|---|---|
| ThatOpen AGPL | `@thatopen/components` is AGPL-3.0. For commercial deployment, obtain a commercial license from That Open Company. |
| gpt-5.4-pro endpoint format | Confirm whether your Azure `gpt-5.4-pro` deployment uses the Responses API or Chat Completions. If Chat Completions, replace `AzureResponsesChatModel` with `AzureChatOpenAI`. |
| Pascal editor npm packages | Not yet published as clean npm bundles. The `VisualEditor.tsx` fallback handles this. Swap for Pascal's `<Viewer>` when available. |
| IfcOpenShell version | Use the latest release from PyPI or conda-forge. The `api.geometry.add_railing_representation` and `add_door_representation` require IfcOpenShell >= 0.7.x. |
| bSDD API auth | Non-secured endpoints (search, class details) work without a Client ID. Secured write endpoints require MSAL registration. For v2, read-only bSDD queries are sufficient. |
| Supabase Storage public URLs | IFC files contain potentially sensitive client data. Set the `ifc-files` bucket to **private** and use signed URLs (`create_signed_url`) rather than public URLs in production. |
