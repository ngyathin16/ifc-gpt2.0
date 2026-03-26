"""Quick inspection of a generated IFC file."""
from __future__ import annotations

import sys
import ifcopenshell

path = sys.argv[1] if len(sys.argv) > 1 else "workspace/4ef3c984.ifc"
f = ifcopenshell.open(path)

print(f"Schema: {f.schema}")
print()

types: dict[str, int] = {}
for e in f.by_type("IfcProduct"):
    t = e.is_a()
    types[t] = types.get(t, 0) + 1
print("Element counts:")
for t, c in sorted(types.items()):
    print(f"  {t}: {c}")

print("\n--- Walls ---")
for w in f.by_type("IfcWall"):
    print(f"  {w.Name}: Rep={bool(w.Representation)}")

print("\n--- Slabs ---")
for s in f.by_type("IfcSlab"):
    print(f"  {s.Name}: type={s.PredefinedType}, Rep={bool(s.Representation)}")

print("\n--- Roofs ---")
for r in f.by_type("IfcRoof"):
    print(f"  {r.Name}: type={r.PredefinedType}, Rep={bool(r.Representation)}")

print("\n--- Doors ---")
for d in f.by_type("IfcDoor"):
    print(f"  {d.Name}: FillsVoids={bool(d.FillsVoids)}, Rep={bool(d.Representation)}")

print("\n--- Windows ---")
for w in f.by_type("IfcWindow"):
    print(f"  {w.Name}: FillsVoids={bool(w.FillsVoids)}, Rep={bool(w.Representation)}")

print("\n--- Openings ---")
for o in f.by_type("IfcOpeningElement"):
    voids = o.VoidsElements
    host = voids[0].RelatingBuildingElement.Name if voids else "NONE"
    fills = o.HasFillings
    filler = fills[0].RelatedBuildingElement.Name if fills else "NONE"
    print(f"  {o.Name}: voids={host}, fills={filler}")

print("\n--- Storeys ---")
for s in f.by_type("IfcBuildingStorey"):
    contained = []
    for rel in getattr(s, "ContainsElements", []):
        for elem in rel.RelatedElements:
            contained.append(elem.is_a())
    print(f"  {s.Name} (elev={s.Elevation}): {len(contained)} elements")
