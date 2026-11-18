"""Measure end-to-end inference time, so no speed claim in the README or on the page is unsupported.

PyTorch path: ClipHeadClassifier.predict() on real photos (TrashNet 512x384 and TACO crops), after warm-up, one at a time.
Browser path (optional, needs playwright and a server for _site on the given URL): time from choosing a sample photo to the
verdict appearing, with the model already loaded.
Usage: python scripts/benchmark_latency.py [http://localhost:8003/]   -> eval/latency.json
"""
import glob
import json
import platform
import statistics
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from curbcheck.model import ClipHeadClassifier


def pct(v, q):
    return float(np.percentile(v, q))


def torch_path():
    import torch
    clf = ClipHeadClassifier()
    files = sorted(glob.glob(str(ROOT / "data/raw/trashnet/dataset-resized/*/*.jpg")))[::40][:50] + sorted(glob.glob(str(ROOT / "data/raw/taco/crops/*.jpg")))[:50]
    for f in files[:3]:
        clf.predict(Image.open(f))  # warm-up
    times = []
    for f in files:
        t = time.perf_counter()
        clf.predict(Image.open(f))
        times.append((time.perf_counter() - t) * 1000)
    return {"images": len(files), "median_ms": statistics.median(times), "p95_ms": pct(times, 95), "max_ms": max(times),
            "threads": torch.get_num_threads()}


def browser_path(url):
    from playwright.sync_api import sync_playwright
    times = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        pg.goto(url)
        pg.wait_for_function("document.querySelector('#status').textContent.startsWith('Model ready')", timeout=600000)
        for n in ("glass20", "glass122", "cardboard30", "metal10", "paper40", "trash7") * 2:
            pg.evaluate("document.querySelector('#result').innerHTML=''")
            t = time.perf_counter()
            pg.click(f"img[data-n={n}]")
            pg.wait_for_function("document.querySelector('#result .verdict')", timeout=60000)
            times.append((time.perf_counter() - t) * 1000)
        b.close()
    return {"photos": len(times), "median_ms": statistics.median(times), "p95_ms": pct(times, 95)}


def main():
    out = {"machine": {"cpu": platform.processor(), "system": platform.platform(), "python": platform.python_version()},
           "pytorch_cpu_per_photo": torch_path()}
    if len(sys.argv) > 1:
        out["browser_per_photo_model_loaded"] = browser_path(sys.argv[1])
    (ROOT / "eval/latency.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
