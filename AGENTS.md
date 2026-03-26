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
