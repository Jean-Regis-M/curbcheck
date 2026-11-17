"""Build the static GitHub Pages demo into _site/: web UI + in-browser engine + head weights + city rules.
The browser runs OpenAI CLIP ViT-B/32 (ONNX, int8) via transformers.js and the same linear head and rules as the API.
Usage: python scripts/build_site.py"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from curbcheck.rules import list_cities, load_city
from curbcheck.taxonomy import ITEMS

OUT = ROOT / "_site"


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "web", OUT)
    (OUT / "rules").mkdir()
    cities = []
    for cid in list_cities():
        shutil.copy(ROOT / "data/rules" / f"{cid}.json", OUT / "rules" / f"{cid}.json")
        c = load_city(cid)
        cities.append({"id": cid, "city": c.city, "program": c.program, "sources": [s.model_dump() for s in c.sources]})
    (OUT / "cities.json").write_text(json.dumps(cities), encoding="utf-8")
    h = np.load(ROOT / "models/head_web.npz", allow_pickle=False)
    head = {"W": np.round(h["W"], 6).tolist(), "b": h["b"].tolist(), "T": float(h["T"]), "threshold": float(h["threshold"]),
            "classes": [str(c) for c in h["classes"]], "labels": ITEMS}
    (OUT / "head.json").write_text(json.dumps(head), encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    print("site built:", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
