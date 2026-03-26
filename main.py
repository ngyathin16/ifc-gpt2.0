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
