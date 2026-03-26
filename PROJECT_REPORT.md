# IFC-GPT v2 — Executive Report

**Date:** March 26, 2026
**Status:** ✅ Complete and operational
**Tests:** 187/187 passing

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
| **Intake** | Receives the user's text, voice, or drawn floor plan |
| **Clarify** | Fills in the gaps — if you say "a house", it picks reasonable defaults for number of rooms, wall heights, materials, etc. |
| **Plan** | The AI writes a detailed building plan in structured JSON format — every wall, column, slab, door, window, staircase, with exact coordinates |
| **Build** | The plan gets turned into an actual IFC file using our building block library (17 element types, 6 assembly kits, 5 type libraries) |
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
- **Pre-built assemblies**: apartment units, stair cores, toilet cores, facade bays, structural grids, roof assemblies

Every element gets proper IFC metadata: spatial containment (which floor it's on), property sets (fire rating, is it external, thermal transmittance), material assignments, and type classification.

---

## What Can Users Actually Do?

| Input Method | How It Works |
|---|---|
| **Text** | Type a description in natural language |
| **Voice** | Speak into the microphone (OpenAI Whisper transcription) |
| **Draw** | Use the visual editor canvas to sketch a floor plan |
| **Upload** | Upload an image/PDF of a floor plan (AI extracts walls and rooms) |

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
| Python source files | 60+ |
| TypeScript/React components | 13 |
| Automated tests | **187 (all passing)** |
| Building element primitives | 17 |
| Assembly kits | 6 |
| Type libraries | 5 (wall, column, beam, door, window) |
| Validation checks | 20+ across 4 layers |
| API endpoints | 8 |
| Pipeline end-to-end time | ~2 minutes |
| Largest tested build | 20-storey highrise, 2,217 elements, ~23 seconds |

---

## What's Left / Future Work

The core system is **complete and functional**. Areas for future enhancement:

- **Element-level modification** — Currently re-generates the whole model; future versions will edit individual elements in-place
- **Multi-user collaboration** — Database and auth are in place; real-time sync would be an addition
- **More building types** — The library handles residential and commercial; specialized types (hospitals, schools) would need additional assembly kits
- **Performance at scale** — 20 storeys works well; 50+ storey supertalls would need optimization

---

## Summary

IFC-GPT v2 is a **working, tested, end-to-end AI-powered BIM generation platform**. It takes natural language input and produces internationally-standardized building models in under 2 minutes. The entire system runs in a web browser — no desktop software, no plugins, no installations. It is built on production-grade technology, has 187 automated tests, 4 layers of validation, and has been proven on buildings up to 20 storeys with 2,000+ elements.

It turns *"build me an apartment building"* into a real, usable, standards-compliant architectural model. Automatically.
