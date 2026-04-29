"""
Render the LangGraph pipeline as a PNG and print an ASCII diagram.

Run with:  uv run python -m scripts.visualize_pipeline
Output:    data/pipeline_graph.png  (open in any image viewer)
"""
import sys
import pathlib

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from src.graph.pipeline import pipeline

out_dir = pathlib.Path("data")
out_dir.mkdir(exist_ok=True)

# ── ASCII diagram (always works, no extra deps) ───────────────────────────────
print("\n── Pipeline Graph (ASCII) ──────────────────────────────────────────")
try:
    print(pipeline.get_graph().draw_ascii())
except Exception as e:
    print(f"  ASCII draw failed: {e}")

# ── Mermaid source ────────────────────────────────────────────────────────────
print("\n── Pipeline Graph (Mermaid) ────────────────────────────────────────")
try:
    mermaid_src = pipeline.get_graph().draw_mermaid()
    print(mermaid_src)
    (out_dir / "pipeline_graph.mmd").write_text(mermaid_src, encoding="utf-8")
    print(f"  Saved: data/pipeline_graph.mmd")
except Exception as e:
    print(f"  Mermaid draw failed: {e}")

# ── PNG (requires pygraphviz or pillow+cairosvg; graceful fallback) ───────────
print("\n── Pipeline Graph (PNG) ────────────────────────────────────────────")
try:
    png_bytes = pipeline.get_graph().draw_mermaid_png()
    png_path = out_dir / "pipeline_graph.png"
    png_path.write_bytes(png_bytes)
    print(f"  Saved: {png_path.resolve()}")
    print("  Open data/pipeline_graph.png in any image viewer.")
except Exception as e:
    print(f"  PNG render unavailable ({e})")
    print("  Use the Mermaid source in data/pipeline_graph.mmd instead.")
    print("  Paste it at https://mermaid.live to view interactively.")
