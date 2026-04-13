# IFC-GPT v2 — Executive Report

**Date:** April 8, 2026
**Status:** ✅ Complete and operational
**Tests:** 249/249 passing

---

## What Is This Project?

IFC-GPT is a web application that **turns plain English into 3D building models**.

A user types something like *"a 10-storey apartment building with balconies"*, and the system automatically generates a full, standards-compliant building information model (BIM) file — the same kind of file that architects and engineers use in professional tools like Revit, ArchiCAD, or Tekla.

Think of it as **ChatGPT, but instead of writing essays, it draws buildings**.

---

## Why Does This Matter?

Creating a BIM model normally takes an architect **days or weeks** using specialized desktop software that costs thousands of dollars per license. This tool does it in **under 2 minutes**, from a single sentence, inside a web browser. No software installation needed.

The output is an **IFC file** — an open, international standard format (like PDF but for buildings). It works with every major architecture/engineering tool on the planet. This is not a toy 3D model — it contains real structural data: wall thicknesses, material layers, fire ratings, spatial containment, property sets, the works.

---

## How Does It Work? (The Simple Version)

```
User types "a house" → AI understands what you mean → AI draws up a plan →
Software builds the 3D model → Quality checks run automatically →
User sees it in their browser
```

That's it. Six steps, fully automatic.

---

## How Does It Work? (The Slightly Less Simple Version)

There are two big pieces:

### 1. The Brain (AI Pipeline)

An AI agent powered by **GPT-5.4-pro** (Microsoft/OpenAI's latest model) takes the user's request through a structured pipeline:

| Step | What Happens |
|------|-------------|
| **Intake** | Receives the user's text, voice, drawn floor plan, or uploaded floor plan image/PDF |
| **Clarify** | Fills in the gaps — if you say "a house", it picks reasonable defaults for number of rooms, wall heights, materials, etc. The user can review and toggle building features in an interactive picker before generation begins. |
| **Plan** | The AI writes a detailed building plan in structured JSON format — every wall, column, slab, door, window, staircase, with exact coordinates |
| **Build** | The plan gets turned into an actual IFC file using our building block library (17 element types, 6 assembly kits, 5 type libraries, MiC room catalog) |
| **Validate** | Four layers of automated quality checks catch errors before the user ever sees them |
| **Repair** | If validation finds problems, the AI fixes them automatically and re-builds (up to 2 attempts) |
| **Export** | The finished file is saved and served to the browser |

### 2. The Body (Building Block Library)

This is our secret sauce. We wrote a **complete IFC authoring engine in pure Python** — no dependency on any desktop software. It can create:

- **Walls** (exterior, interior, curtain walls) with material layer sets
- **Columns** (rectangular, circular, I-section steel) with profile sets
- **Beams** (concrete, steel) with span validation
- **Slabs** (floor, roof, landing) from arbitrary polygon outlines
- **Doors & Windows** with automatic wall openings
- **Stairs** (with treads, risers, proper geometry)
- **Railings, Roofs** (flat and pitched), **Ramps, Footings, Coverings**
- **Elevators** (shaft enclosures)
- **Balconies** (cantilevered slab + safety railing)
- **Pre-built assemblies** (7): apartment units, stair cores, toilet cores, facade bays, structural grids, roof assemblies, **MiC modules**
- **MiC room catalog**: 33 modular construction module types with **real measured dimensions** extracted from 49 individual IFC files of the HSK Hong Kong MiC housing project — used for room classification, size validation, and parametric module generation

Every element gets proper IFC metadata: spatial containment (which floor it's on), property sets (fire rating, is it external, thermal transmittance), material assignments, and type classification.

---

## What Can Users Actually Do?

| Input Method | How It Works |
|---|---|
| **Text** | Type a description in natural language → review inferred building features in an interactive picker → confirm and generate |
| **Voice** | Speak into the microphone (OpenAI Whisper transcription) |
| **Draw** | Use the visual editor canvas to sketch a floor plan |
| **Upload** | Upload a PDF/image floor plan — two-branch AI detection (VLM for semantics + OpenCV for geometry), review detected plan, then confirm to build |

The text/voice flow now includes a **Feature Picker** step: after the user submits a prompt, the system infers building type, storey count, and default features. The user sees a grouped, toggleable feature menu (23 features across 8 categories) and can customise before generation begins. Conflicting features (e.g. "curtain wall" vs "exterior walls") are automatically resolved.

The output appears as an **interactive 3D model** in the browser. Users can orbit, zoom, click on elements to inspect them, and request modifications ("make the kitchen wall 1 meter longer").

---

## Quality Assurance — We Don't Ship Broken Buildings

The system runs **4 layers of validation** on every model:

1. **Plan checks** (before building) — Are the walls forming closed rooms? Are doors actually inside walls? Are beams not wider than the walls they sit on?
2. **Schema validation** — Does the IFC file conform to the international IFC4 standard?
3. **IDS specification checks** — Does it pass buildingSMART's own compliance tests? (We test against 3 specification files including Hong Kong building code requirements)
4. **Semantic checks** — Are elements properly contained in storeys? Is there geometry on every element? Are columns aligned vertically across floors?

If anything fails, the AI **automatically fixes it** without the user needing to do anything.

---

## Technology Stack

| Layer | Technology | Plain English |
|---|---|---|
| AI Model | GPT-5.4-pro (Azure) | Microsoft's most powerful AI, hosted in their cloud |
| AI Orchestration | LangGraph | Manages the multi-step pipeline |
| IFC Engine | IfcOpenShell (Python) | Open-source library for reading/writing building files |
| Validation | ifctester + custom checks | Official buildingSMART testing tools |
| Backend Server | FastAPI (Python) | High-performance API server |
| Frontend | Next.js 15 + React | Modern web framework (same as used by Netflix, Uber, etc.) |
| 3D Viewer | ThatOpen Components | In-browser IFC viewer using WebGL |
| UI Components | shadcn/ui + Tailwind CSS | Clean, modern interface components |
| Animations | Framer Motion | Smooth transitions and micro-interactions |
| Database | Supabase (PostgreSQL) | User accounts, project history, file storage |
| Building Data | bSDD API | Official buildingSMART Data Dictionary for property standards |

---

## Current Numbers

| Metric | Value |
|---|---|
| Python source files | 70+ |
| TypeScript/React components | 15 (9 main + 6 shadcn/ui) |
| Automated tests | **249 (all passing)** |
| Building element primitives | 17 |
| Assembly kits | 7 (structural_grid, stair_core, toilet_core, apartment_unit, facade_bay, roof_assembly, mic_module) |
| Type libraries | 5 (wall, column, beam, door, window) |
| User-selectable building features | **23** across 8 categories |
| MiC room catalog modules | **33** unique types (measured from 49 real HK MiC IFC files) |
| Validation checks | 30+ across 4 layers (17 plan + schema + 3 IDS + 13 semantic) |
| API endpoints | 13 across 8 route modules (including features/infer, features catalog, floorplan) |
| Pipeline end-to-end time | ~2 minutes (text), ~5 seconds (floor plan detection) |
| Largest tested build | **20-storey highrise, all 18 features enabled, 2,702 elements, 5.9 MB IFC, ~27 seconds** |

---

## Recent Additions (March 27–31, 2026)

### MiC IFC Analysis → Real-Data Building Blocks

All **49 individual MiC IFC files** from the HSK Hong Kong MiC housing project were parsed and analysed. Bounding-box geometry extraction (handling both `IfcFacetedBrep` and `IfcFaceBasedSurfaceModel` via `IfcMappedItem`) yielded real measured dimensions for **33 unique module types** across 10 room categories. The results:

| Category | MiC Types | Typical Size (W × D × H) |
|---|---|---|
| Master Bedroom (TYPE 1.x) | 7 variants | 2.39 × 4.0 m × 3.15 m |
| Bathroom (TYPE 2.x) | 3 variants | 2.39 × 5.75 m × 3.15 m |
| 2-Bed Bathroom (TYPE 2B) | 4 variants | 2.39 × 6.69 m × 3.15 m |
| Living/Kitchen (TYPE 3 LK) | 6 variants | 2.76 × 7.05 m × 3.40 m |
| Living/Dining (TYPE 3 LD) | 4 variants | 2.76 × 7.13 m × 3.40 m |
| Kitchen (TYPE 4.x) | 2 variants | 1.73 × 3.27 m × 3.09 m |
| Bedroom (TYPE 5.x) | 2 variants | 2.39 × 4.0 m × 3.15 m |
| Toilet (TYPE 6) | 1 variant | 1.89 × 3.08 m × 3.09 m |
| Utility (TYPE 7–10) | 4 variants | 1.15–2.68 × 2.26–4.47 m |

These dimensions replaced previous estimates in `mic_catalog.py` and power a new **MiC Module Assembly** (`building_blocks/assemblies/mic_module.py`) that generates parametric room modules using existing wall/slab/door/window primitives.

### Interactive Feature Picker UI

The frontend now has a **two-step generation flow**:

1. User types a building description → clicks **"Next — Pick Features"**
2. System instantly infers building type, storey count, and default features (heuristic — no LLM call)
3. **Feature Picker** panel appears: 23 features grouped into 8 categories, each with a toggle checkbox, label, and description
4. Conflicting features auto-resolve (e.g. toggling "Interior partitions" removes "Open-plan floors")
5. User clicks **"Generate"** → the selected features are sent alongside the prompt to the pipeline

New files: `web/components/FeaturePicker.tsx`, updated `web/lib/api.ts` (+ `getFeatures`, `inferFeatures`), `api/routes/features.py` (+ `conflicts_with` field).

### 8 New MiC-Derived Building Features

Extracted from the MiC material/geometry analysis and wired end-to-end (schema → build node → plan generator → API → feature picker UI):

| Feature | IFC Element | Source |
|---|---|---|
| Foundation footings | `IfcFooting` pad footings under columns | Structural analysis |
| Balconies | `IfcSlab` + `IfcRailing` cantilevered slab | MiC facade materials |
| Roof parapets | `IfcWall` low perimeter walls | MiC building envelope |
| Suspended ceilings | `IfcCovering` CEILING (aluminium tile) | MiC TYPE 2/6 bathroom modules |
| Floor finishes | `IfcCovering` FLOORING (homogeneous tile) | MiC TYPE 1–5 floor materials |
| Accessibility ramps | `IfcRamp` 1:12 gradient | HK building code |
| Bathroom pods | Walls + door (MiC ~2.4 × 5.8 m) | MiC TYPE 2.x measured dims |
| Service rooms | Walls + door (E&M/refuse ~4.5 × 2.7 m) | MiC TYPE 7–10 measured dims |

---

## Documentation Updates (April 8, 2026)

All documentation files have been audited and synchronised with the codebase:

- **README.md** — Updated test count (249), assembly count (7), component count (15), MiC catalog (33 types), validation checks (30+)
- **ISSUES.json** — Updated project_status with all phases including FloorPlan2IFC, MiC, and Features
- **AUDIT_ISSUES.json** — Updated implementation_status with accurate file counts, phase 7–9 completion
- **MANUAL_STEPS.md** — Corrected test count to 249
- **AGENTS.md** — Verified accurate (no changes needed)

---

## What's Left / Future Work

The core system is **complete and functional**. Areas for future enhancement:

- **Element-level modification** — Currently re-generates the whole model; future versions will edit individual elements in-place
- **Multi-user collaboration** — Database and auth are in place; real-time sync would be an addition
- **More building types** — The library handles residential and commercial; specialized types (hospitals, schools) would need additional assembly kits
- **Performance at scale** — 20 storeys works well; 50+ storey supertalls would need optimization
- **Fine-tuned YOLO model** — Replace VLM branch with a trained model on CubiCasa5K/FloorPlanCAD for 70-90% recall (currently ~50-65% with VLM)
- **Plan overlay UI** — Frontend component to visualize detected walls/openings overlaid on the original floor plan image before confirmation

---

## Summary

IFC-GPT v2 is a **working, tested, end-to-end AI-powered BIM generation platform**. It takes natural language, voice, drawn plans, or uploaded floor plan images and produces internationally-standardized building models in under 2 minutes. The entire system runs in a web browser — no desktop software, no plugins, no installations. It is built on production-grade technology, has **249 automated tests** across 26 test files, **30+ validation checks** across 4 layers, a MiC room dimension catalog derived from **49 real Hong Kong IFC files (33 unique module types)**, **7 assembly kits**, **23 user-selectable building features** with an interactive picker UI, **15 frontend components** (9 main + 6 shadcn/ui), and has been proven on buildings up to **20 storeys with 2,702 elements**.

It turns *"build me an apartment building"* — or an uploaded floor plan PDF — into a real, usable, standards-compliant architectural model. Automatically.
