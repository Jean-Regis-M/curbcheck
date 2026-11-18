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


def head_dict():
    h = np.load(ROOT / "models/head_web.npz", allow_pickle=False)
    extra = {"zs_text": np.round(h["zs_text"], 5).tolist(), "zs_scale": float(h["zs_scale"])} if "zs_text" in h.files else {}
    return {**extra, "W": np.round(h["W"], 6).tolist(), "b": h["b"].tolist(), "T": float(h["T"]), "threshold": float(h["threshold"]),
            "classes": [str(c) for c in h["classes"]], "labels": ITEMS}


def evidence_dict():
    """Numbers shown on the page, read from the evaluation files so the page cannot drift from the evidence."""
    key = "zs2.0|None|cov0.55"
    web = ROOT / "eval/v3_web.json"
    src = json.loads((web if web.exists() else ROOT / "eval/v3.json").read_text("utf-8"))
    base = json.loads((ROOT / "eval/v3.json").read_text("utf-8"))
    names = {"seattle": "Seattle", "washington_dc": "Washington DC", "new_york": "New York", "austin": "Austin",
             "minneapolis": "Minneapolis", "boston": "Boston", "san_francisco": "San Francisco"}
    sets = {"TrashNet": "A_train_TACO_RealWaste_test_TrashNet", "RealWaste": "B_train_TACO_TrashNet_test_RealWaste"}
    out = {"model": "browser" if web.exists() else "pytorch", "datasets": {}}
    for ds, k in sets.items():
        rows = []
        for cid, nm in names.items():
            r, b = src[k][key]["cities"][cid], base["v1_baseline_same_sets"][ds][cid]
            rows.append({"city": nm, "forced": r["forced_false_accept_rate"], "shipped": r["false_accept_rate"], "missed": r["missed_recyclable_rate"],
                         "coverage": r["coverage"], "v1_far": b["false_accept_rate"], "v1_missed": b["missed_recyclable_rate"], "v1_coverage": b["coverage"]})
        out["datasets"][ds] = rows
    quoted = audited = total = 0
    for cid in list_cities():
        for rule in load_city(cid).rules.values():
            total += 1
            quoted += bool(rule.quote)
            audited += bool(rule.quote) and cid != "new_york"
    out["rules"] = {"total": total, "quoted": quoted, "audited_by_script": audited, "cities": len(list_cities())}
    lat = ROOT / "eval/latency.json"
    if lat.exists():
        out["latency"] = json.loads(lat.read_text("utf-8"))
    return out


def main():
    OUT.mkdir(exist_ok=True)
    for child in OUT.iterdir():  # empty the folder instead of deleting it, so a server running inside it keeps working
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    shutil.copytree(ROOT / "web", OUT, dirs_exist_ok=True)
    (OUT / "rules").mkdir()
    cities = []
    for cid in list_cities():
        shutil.copy(ROOT / "data/rules" / f"{cid}.json", OUT / "rules" / f"{cid}.json")
        c = load_city(cid)
        cities.append({"id": cid, "city": c.city, "program": c.program, "sources": [s.model_dump() for s in c.sources]})
    (OUT / "cities.json").write_text(json.dumps(cities), encoding="utf-8")
    (OUT / "evidence.json").write_text(json.dumps(evidence_dict()), encoding="utf-8")
    (OUT / "head.json").write_text(json.dumps(head_dict()), encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    print("site built:", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
