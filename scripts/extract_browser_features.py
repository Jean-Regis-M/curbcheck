"""Compute features with the exact in-browser pipeline (transformers.js, int8 CLIP) for the TACO crops (and optionally
TrashNet), via headless Chromium, so the shipped web head is trained and evaluated on browser features.
Needs: playwright + a server for _site on :8002 (python -m http.server 8002 --directory _site).
Usage: python extract_browser_features.py taco|trashnet OUT.json"""
import base64
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
which, out = sys.argv[1], sys.argv[2]
if which == "realwaste":
    import io
    import re

    import pyarrow.parquet as pq
    recs = []
    for shard in sorted((RAW / "realwaste").glob("p*.parquet")):
        recs += pq.read_table(shard, columns=["image"]).column("image").to_pylist()
    labels = [re.sub(r"_\d+\.\w+$", "", r["path"]) for r in recs]
    files = [io.BytesIO(r["bytes"]) for r in recs]
    names = labels
elif which == "taco":
    files = [RAW / "taco/crops" / r["crop"] for r in json.loads((RAW / "taco/crops.json").read_text("utf-8"))]
else:
    files = sorted(p for c in ("cardboard", "glass", "metal", "paper", "plastic", "trash") for p in (RAW / "trashnet/dataset-resized" / c).glob("*.jpg"))
feats = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto("http://localhost:8003/")
    pg.wait_for_function("document.querySelector('#status').textContent.startsWith('Model ready')", timeout=600000)
    t = time.time()
    for i, f in enumerate(files):
        d = base64.b64encode(f.getvalue() if hasattr(f, "getvalue") else f.read_bytes()).decode()
        feats.append(pg.evaluate("async d=>{const b=Uint8Array.from(atob(d),c=>c.charCodeAt(0));return await engine.embed(new File([b],'x.jpg',{type:'image/jpeg'}))}", d))
        if i % 50 == 0:
            print(i, len(files), round(time.time() - t), "s", flush=True)
    b.close()
Path(out).write_text(json.dumps({"files": [str(f) for f in (names if which == "realwaste" else files)], "feats": feats}), encoding="utf-8")
print("done", len(feats))
