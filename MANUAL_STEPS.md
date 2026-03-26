# Manual Steps

Everything the codebase needs that **cannot** be done by Cascade.

---

## 1. Environment Variables

Copy `.env.example` to `.env` and fill in real values:

```
AZURE_OPENAI_ENDPOINT=<your Azure OpenAI endpoint>
AZURE_OPENAI_API_KEY=<your Azure OpenAI key>
SUPABASE_URL=<your Supabase project URL>
SUPABASE_JWT_SECRET=<Settings → API → JWT Secret>
SUPABASE_SERVICE_ROLE_KEY=<Settings → API → service_role key>
FRONTEND_ORIGIN=http://localhost:3000
WORKSPACE_DIR=./workspace
```

Frontend (`web/.env.local`):

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_SUPABASE_URL=<same as SUPABASE_URL>
NEXT_PUBLIC_SUPABASE_ANON_KEY=<Settings → API → anon key>
```

---

## 2. Supabase Setup

1. **Create a Supabase project** at [supabase.com](https://supabase.com).
2. **Run the schema** — paste `supabase/schema.sql` into the SQL Editor and execute.
3. **Create a Storage bucket** named `ifc-files` (Settings → Storage → New Bucket). Set it to **private**.
4. **Enable email auth** — Authentication → Providers → Email (should be on by default).

---

## 3. Install Dependencies

Backend:

```bash
uv sync
```

Frontend:

```bash
cd web && npm install
```

---

## 4. Run the App

Terminal 1 — API server:

```bash
uv run uvicorn api.server:app --reload --port 8000
```

Terminal 2 — Next.js dev server:

```bash
cd web && npm run dev
```

---

## 5. Run Tests

```bash
uv run pytest tests/ -v
```

All 187 tests should pass. No external services needed for tests.

---

## 6. FloorPlan2IFC — First Run Setup

The floor plan upload feature requires **EasyOCR** which downloads language models on first use (~100 MB).

1. **Trigger model download** (one time):
   ```bash
   uv run python -c "import easyocr; easyocr.Reader(['en'], gpu=False)"
   ```
   This downloads the English text detection + recognition models to `~/.EasyOCR/`.

2. **GPU acceleration (optional)**: If you have an NVIDIA GPU and want faster OCR, install the CUDA-enabled PyTorch:
   ```bash
   uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   ```
   Then EasyOCR will automatically use the GPU.

3. **Known limitations** (v1):
   - Scale detection works best on digital floor plans with a visible "1:100" annotation or scale bar.
   - Handwritten / low-quality scanned plans have ~40-60% wall recall — the system will warn the user.
   - Only walls and rooms are detected in v1 (OpenCV backend). Doors, windows, columns require the VLM or YOLO upgrade (v2).
   - The Y-axis flip happens once in `floorplan/vectorise.py` — never flip manually.

---

## 7. Optional: Deploy

- **Backend** — any Python host (Railway, Fly.io, etc.). Set all env vars from step 1. Note: EasyOCR + PyTorch adds ~1.5 GB to the Docker image. Use a multi-stage build or `--no-deps` torch CPU wheel to reduce size.
- **Frontend** — Vercel (`cd web && vercel`). Set `NEXT_PUBLIC_*` env vars in project settings.
- Once deployed, update `FRONTEND_ORIGIN` to the real frontend URL for CORS.
