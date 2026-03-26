# IFC-GPT v2

> AI-powered BIM generation — turn plain English into standards-compliant IFC4 building models, entirely in the browser.

[![Tests](https://img.shields.io/badge/tests-187%2F187%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![Next.js](https://img.shields.io/badge/Next.js-15-black)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

---

## Overview

IFC-GPT v2 is a full-stack web application that generates IFC4 building information models from natural language prompts. Type *"a 10-storey apartment building with balconies"* and get a complete, validated BIM file in under 2 minutes.

**No Blender. No desktop software. No plugins.** Pure Python IFC authoring + browser-based 3D viewer.

### Key Features

- **Text-to-BIM** — Describe a building in plain English, get a standards-compliant IFC file
- **Voice input** — Speak your building description (OpenAI Whisper)
- **Visual editor** — Draw floor plans on a canvas, convert to BIM
- **Floor plan upload** — Upload a PDF/image floor plan, AI extracts geometry
- **In-browser 3D viewer** — ThatOpen Components (Three.js + web-ifc WASM)
- **Element modification** — Click elements in the viewer, modify via natural language
- **4-layer validation** — Plan checks, IFC4 schema, IDS specs, semantic analysis
- **Auto-repair** — AI automatically fixes validation errors and re-builds
- **bSDD integration** — Standard property sets from the buildingSMART Data Dictionary

---

## Architecture

```
Browser (Next.js 15)                    Python Backend (FastAPI)
┌─────────────────────┐                ┌──────────────────────────┐
│ Chat / Voice / Draw │───REST/SSE───▶│ LangGraph Agent Pipeline │
│ ThatOpen 3D Viewer  │◀─────────────│ intake → clarify → plan  │
│ shadcn/ui + Tailwind│               │ → build → validate →     │
│ Framer Motion       │               │ repair → export          │
└─────────────────────┘                └───────────┬──────────────┘
                                                   │
                                       ┌───────────▼──────────────┐
                                       │ IfcOpenShell Authoring   │
                                       │ 17 primitives · 6 kits  │
                                       │ 5 type libs · 20+ checks│
                                       └──────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### 1. Clone & install

```bash
git clone https://github.com/ngyathin16/ifc-gpt2.0.git
cd ifc-gpt2.0

# Python dependencies
uv sync

# Frontend dependencies
cd web && npm install && cd ..
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys:
#   AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT  (or OPENAI_API_KEY)
#   SUPABASE_URL + SUPABASE_ANON_KEY              (optional, for auth)
```

### 3. Run

```bash
# Terminal 1: Backend (port 8000)
uv run python main.py

# Terminal 2: Frontend (port 3000)
cd web && npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and start building.

---

## Project Structure

```
├── agent/                  # LangGraph AI pipeline
│   ├── nodes/              # 7 pipeline stages (intake → export)
│   ├── schemas.py          # BuildingPlan Pydantic model
│   ├── llm.py              # GPT-5.4-pro client (Azure Responses API)
│   └── prompts/            # System, plan, and repair prompts
│
├── api/                    # FastAPI HTTP server
│   ├── routes/             # 8 endpoints (generate, build, modify, voice, etc.)
│   ├── deps.py             # Supabase JWT verification
│   └── storage.py          # Supabase Storage upload
│
├── building_blocks/        # IFC authoring engine (pure Python, no Blender)
│   ├── primitives/         # 17 element types (wall, column, beam, slab, door, ...)
│   ├── types/              # 5 type libraries (IfcWallType, IfcColumnType, ...)
│   ├── assemblies/         # 6 assembly kits (apartment, stair core, facade, ...)
│   ├── psets.py            # Standard property set helpers
│   ├── bsdd.py             # bSDD API client with fallback cache
│   └── context.py          # IFC project/site/building/storey setup
│
├── validation/             # 4-layer validation system
│   ├── plan_checks.py      # Pre-build plan validation (geometry, logic)
│   ├── schema_check.py     # IFC4 schema compliance
│   ├── runner.py           # IDS specification testing (ifctester)
│   ├── semantic_checks.py  # Post-build spatial/geometry analysis
│   └── ids/                # IDS specification files
│
├── web/                    # Next.js 15 frontend
│   ├── components/         # 7 main + 6 shadcn/ui components
│   ├── hooks/              # useJob, usePascalEditor, useVoice
│   ├── lib/                # API client, Supabase, plan converter
│   └── types/              # TypeScript BuildingPlan types
│
├── tests/                  # 187 tests across 26 files
├── supabase/               # Database schema with RLS
└── floorplan/              # Floor plan image → BIM pipeline
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/generate` | Text prompt → IFC generation |
| `POST` | `/api/build-from-plan` | BuildingPlan JSON → IFC |
| `POST` | `/api/modify` | GUID + instruction → modified IFC |
| `POST` | `/api/voice` | Audio upload → Whisper → IFC generation |
| `POST` | `/api/floorplan` | Floor plan image/PDF → IFC |
| `GET`  | `/api/status/{id}/stream` | SSE job status stream |
| `GET`  | `/api/features` | Building feature catalog |
| `GET`  | `/api/bsdd/*` | bSDD property lookups |

---

## Building Blocks

### Primitives (17)

`wall` · `column` · `beam` · `slab` · `door` · `window` · `opening` · `roof` · `stair` · `railing` · `ramp` · `curtain_wall` · `covering` · `member` · `footing` · `elevator`

### Type Libraries (5)

`wall_types` (exterior/interior with material layers) · `column_types` (concrete/circular with profile sets) · `beam_types` (concrete/steel) · `door_types` (single swing/fire) · `window_types` (standard/double-glazed)

### Assemblies (6)

`structural_grid` · `stair_core` · `toilet_core` · `apartment_unit` · `facade_bay` · `roof_assembly`

---

## Validation

Every generated model passes through 4 validation layers:

1. **Plan checks** — Wall enclosure, opening bounds, beam spans, column alignment, elevation consistency
2. **Schema validation** — `ifcopenshell.validate` against IFC4 schema
3. **IDS checks** — `ifctester` against buildingSMART specification files (base, HK code, custom)
4. **Semantic checks** — Spatial containment, element geometry, bounding box sanity, pset compliance

If validation fails, the repair node feeds errors back to the LLM for automatic correction (up to 2 attempts).

---

## Testing

```bash
uv run pytest tests/ -v
```

187 tests covering all primitives, types, assemblies, validation layers, build node dispatch, bSDD integration, storage, and floor plan processing.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Model | GPT-5.4-pro (Azure OpenAI Responses API) |
| Agent | LangGraph |
| IFC Engine | IfcOpenShell |
| Validation | ifctester + IDS |
| Backend | FastAPI + uvicorn |
| Frontend | Next.js 15 (App Router) |
| 3D Viewer | ThatOpen Components (Three.js + web-ifc) |
| UI | shadcn/ui + Tailwind CSS + Framer Motion |
| Database | Supabase (PostgreSQL + Auth + Storage) |
| Voice | OpenAI Whisper |
| Building Data | bSDD REST API |
| Package Management | uv (Python) + npm (Node) |

---

## Environment Variables

See [`.env.example`](.env.example) for the full list. Required:

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_API_KEY` | Azure OpenAI resource key |
| `AZURE_OPENAI_ENDPOINT` | Full Responses API URL with api-version |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name (`gpt-5.4-pro`) |

Optional (for auth/storage):

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anonymous key |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side service role key |
| `SUPABASE_JWT_SECRET` | JWT verification secret |

---

## License

MIT
