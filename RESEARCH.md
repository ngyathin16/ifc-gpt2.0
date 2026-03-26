# RESEARCH — FloorPlan2IFC: Feasibility, State of the Art & Resources

---

## 1. Problem Definition

Automatic conversion of 2D floor plan images (raster PDF, PNG, JPEG, TIFF) into structured 3D BIM models (IFC) is a multi-stage computer vision and geometric reasoning problem. The pipeline must:

1. Ingest and normalise diverse raster input quality
2. Detect the drawing scale
3. Detect and classify architectural elements (walls, openings, rooms, columns, stairs)
4. Convert pixel coordinates to real-world metres
5. Author a valid IFC file from the resulting geometry

Each stage has well-researched solutions in 2026. The pipeline is feasible as a production feature for clean digital floor plans. Handwritten and low-quality scanned plans require additional preprocessing and have lower detection accuracy.

---

## 2. Commercial Evidence: This Is Already Viable

Several commercial tools prove the pipeline is not experimental:

| Tool | Method | Output | Accuracy |
|---|---|---|---|
| **AmpliFy** (INEX BET) | ML model, web app, free | IFC + RVT + DWG | Walls, doors, windows, rooms, shafts auto-detected |
| **WiseBIM AI** | AI Revit plugin | Revit native elements | Detects walls, windows, doors, slabs; seconds per 100m2 plan |
| **Floorplan2IFC** (open source) | CV + heuristics | IFC graph structure | Research quality; no production deployment |

AmpliFy explicitly uses IfcOpenShell for IFC editing and ThatOpen Components for 3D preview — the same stack as IFC-GPT v2. It is open-source on GitHub under GPL-3.0.

WiseBIM achieves detection of a plan of 100m2 in a few seconds and approximately 2 minutes for a 3,000m2 plan.

---

## 3. Detection Accuracy Benchmarks

The key data point for planning accuracy expectations:

> "General-purpose vision AI achieves 40-58% detection on CAD drawings without specialised training. Specialised models trained on floor plan data achieve 70-90%+ detection rates."
> — AIDE AI benchmark on FloorPlanCAD dataset, 100 samples, 28 object categories

This means:
- **v1 using the VLM API with a strong prompt**: expect 50-65% element recall on average floor plans.
- **v2 with fine-tuning on CubiCasa5K**: expect 70-85% recall.
- **v2 with a YOLO model trained on FloorPlanCAD**: expect 75-90% recall on digital CAD-style plans.

---

## 4. Academic Landscape

### 4.1 FloorplanVLM (Feb 2026) — Most Relevant

Reformulates floor plan vectorisation as image-conditioned sequence generation, directly outputting structured JSON representing walls, rooms, and openings. Achieves 92.52% external-wall IoU on FPBENCH-2K. Uses a "Structure-First, Semantics-Second" JSON schema: walls defined first, rooms referencing wall IDs. This is exactly the schema used in IFC-GPT's BuildingPlan.

### 4.2 CubiCasa5K (2019) — Best Fine-tuning Dataset

5,000 floor plan images annotated into 80+ object categories. Split: 4,200 train / 400 val / 400 test. Style variety includes high-quality architectural, B&W CAD, and colorful marketing drawings. Available at github.com/CubiCasa/CubiCasa5k under CC BY 4.0. Recommended for v2 fine-tuning.

### 4.3 FloorPlanCAD (ICCV 2021) — CAD Symbol Detection

10,000+ real-world CAD floor plans with vector annotations for 30 object categories, updated to 15,000+ samples on Hugging Face. Best for training YOLO or CNN-GCN models on CAD-style drawings.

### 4.4 ArchCAD-400K (2025) — Largest Available

413,062 annotated chunks from 5,538 drawings. 26x larger than FloorPlanCAD. Uses a dual-pathway DPSS framework. The largest publicly available dataset for architectural CAD symbol detection.

### 4.5 Deep Floor Plan Recognition (ICCV 2019, Zeng et al.)

VGG encoder with multi-task network and room-boundary-guided attention. Handles non-rectangular layouts and walls of non-uniform thickness. Strong baseline for semantic segmentation.

---

## 5. Technical Approach: Two-Branch Pipeline

Research and production evidence converges on a two-branch architecture:

```
Branch A: Vision LLM (Semantic)        Branch B: OpenCV (Geometric)
  - Room type classification               - HoughLinesP wall lines
  - Element type identification            - Contour detection for rooms
  - Confidence scoring                     - Scale bar detection
         |                                        |
         +------------ MERGE -------------------+
                         |
              Precise geometry + correct semantics
```

Validated by practitioners:
> "Vision LLMs are great at turning diagrams into structured JSON — rooms, areas, layout. But when the image contains printed numbers, OCR is more accurate. Merge OCR dimensions with VLM structure."

The merge step uses VLM for element type and room labels, and OpenCV HoughLinesP for precise pixel coordinates. VLM wall endpoints are snapped to the nearest detected line within a tolerance threshold.

---

## 6. Scale Detection

Two reliable methods:

**Method 1: OCR on scale annotation**
EasyOCR reads the title block (bottom 20% of drawing) for patterns like "1:100" or "Scale 1:50". Regex: `r"(?:scale\s*)?1\s*[:/]\s*(\d+)"`. Results are snapped to known architectural scales [1, 2, 5, 10, 20, 25, 50, 100, 200, 500].

**Method 2: Scale bar detection**
OpenCV HoughLinesP finds the longest near-horizontal line in the lower third of the image. EasyOCR reads the labelled distance (e.g., "0 5 10m"). Scale denominator is derived from bar length vs. labelled real distance.

**Fallback**: Default to 1:100 at 300 DPI (~118.11 px/m). Display a prominent UI warning requiring user confirmation.

---

## 7. Tools and Libraries

| Tool | Purpose | Licence |
|---|---|---|
| PyMuPDF (fitz) | PDF rasterisation at 300 DPI | AGPL-3 |
| Pillow | Image normalisation, resize | MIT |
| OpenCV (opencv-python-headless) | Wall line detection, Canny, HoughLinesP | Apache-2.0 |
| EasyOCR | Scale annotation and text reading | Apache-2.0 |
| pytesseract | Fallback OCR | Apache-2.0 |
| IfcOpenShell | IFC file authoring | LGPL-3.0 |
| ifctester | IDS validation | MIT |
| Ultralytics YOLO (v2 upgrade) | Fine-tuned floor plan detection model | AGPL-3 |
| CubiCasa5K | Fine-tuning dataset | CC BY 4.0 |
| FloorPlanCAD | Fine-tuning dataset | Research use |
| AmpliFy (INEX BET) | Reference implementation | GPL-3.0 |

---

## 8. Coordinate Systems — Critical

Floor plan images use top-left origin, Y increases downward. IFC uses bottom-left origin, Y increases upward. The Y-axis flip must happen exactly once in the pipeline, in `vectorise.py`:

```python
def flip_y(y_px, h_total_px):
    return h_total_px - y_px
```

Never apply this in the VLM prompt, the detection merge, or the plan builder. Applying it twice produces mirror-image geometry.

---

## 9. Known Limitations and Mitigations

| Limitation | Severity | Mitigation |
|---|---|---|
| Handwritten/scanned plans: 20-40% lower recall | High | v1 scope limited to clean digital floor plans |
| Curved walls not supported by HoughLinesP | Medium | VLM detects; map to straight-wall approximations in v1 |
| Scale detection fails on plans with no text | Medium | Fall back to scale bar detection, then 1:100 default |
| A1 plan at 300 DPI = ~10M pixels (VLM cost) | Medium | Clamp image to 4096px longest axis before VLM |
| PyMuPDF is AGPL | Legal | Evaluate pdf2image (MIT) as alternative |
| VLM hallucination | Low | User confirmation overlay is the primary safeguard |

---

## 10. v2 Upgrade Path: Fine-tuned YOLO Model

Replace the VLM branch with a fine-tuned YOLOv8 model trained on CubiCasa5K and FloorPlanCAD:

```python
from ultralytics import YOLO
model = YOLO("models/floorplan_yolov8.pt")
results = model(image_path, conf=0.4)
```

Benefits: runs locally (no API cost), GPU-accelerated, 3-5x faster, achieves 70-90% recall. The `detect.py` module is designed with a pluggable detection backend (`_vlm_detect` vs `_yolo_detect`) to make this upgrade non-breaking.

---

## 11. Strategic Value to IFC-GPT Roadmap

| Roadmap Item | How This Feature Advances It |
|---|---|
| 4.3 Application Consolidation | Floor plan upload replaces text-description of existing buildings |
| 4.4 Granular Building Modification | Detected IFC preserves individual element GUIDs for targeted edits |
| 4.1 Model Upgrades | VLM spatial reasoning is immediately applicable; fine-tuning is the next step |

This feature also opens a new user segment (BIM coordinators digitising legacy drawings) that text-prompt generation cannot reach.

