"""Unseen-dataset test: TrashNet (studio photos, MIT licence) for BOTH heads at their fixed thresholds.
Ground truth only where material decides the verdict: cardboard/glass/metal/paper -> accept, trash -> not accept.
Plastic excluded. Only 137 'trash' images exist, so false-accept intervals are wide."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from curbcheck.decision import decide
from curbcheck.model import ClipHeadClassifier
from curbcheck.rules import list_cities, load_city

CLASSES = {"cardboard": "accept", "glass": "accept", "metal": "accept", "paper": "accept", "trash": "other"}
CITIES = list_cities()


def main():
    base = ROOT / "data/raw/trashnet/dataset-resized"
    files = [(c, f) for c in CLASSES for f in sorted((base / c).glob("*.jpg"))]
    truth = np.array([CLASSES[c] for c, _ in files])
    out = {"n": len(files), "n_not_accept": int((truth == "other").sum()), "heads": {}}
    rng = np.random.default_rng(0)
    for name, path in (("v1", "head_v1.npz"), ("v2", "head_v2.npz")):
        clf = ClipHeadClassifier(ROOT / "models" / path)
        probs = [clf.predict(Image.open(f)) for _, f in files]
        res = {}
        for cid in CITIES:
            city = load_city(cid)
            ds = [decide(p, city, threshold=clf.threshold) for p in probs]
            ans = np.array([d.verdict for d in ds])
            forced = np.array(["accept" if d.p_accept >= d.p_reject else "reject" for d in ds])
            non = truth == "other"

            def far(a, i):
                return ((a[i] == "accept") & non[i]).sum() / max(non[i].sum(), 1)

            def miss(a, i):
                return ((a[i] == "reject") & ~non[i]).sum() / max((~non[i]).sum(), 1)
            n = len(truth)
            allx = np.arange(n)
            bs = [rng.integers(0, n, n) for _ in range(300)]
            fa = (ans == "accept") & non
            res[cid] = {"counts": {"non_accept_items": int(non.sum()), "false_accepts": int(fa.sum()), "answered_accept": int((ans == "accept").sum()),
                                   "accept_precision": float(1 - fa.sum() / max((ans == "accept").sum(), 1))},
                        "coverage": float((ans != "not_sure").mean()),
                        "false_accept_rate": float(far(ans, allx)), "far_ci95": [float(np.percentile([far(ans, i) for i in bs], q)) for q in (2.5, 97.5)],
                        "missed_recyclable_rate": float(miss(ans, allx)), "missed_ci95": [float(np.percentile([miss(ans, i) for i in bs], q)) for q in (2.5, 97.5)],
                        "forced_false_accept_rate": float(far(forced, allx)), "forced_missed_recyclable_rate": float(miss(forced, allx))}
        out["heads"][name] = res
        print(name, {c: {k: round(v, 3) for k, v in r.items() if not k.endswith("ci95") and not isinstance(v, dict)} for c, r in res.items()}, flush=True)
    (ROOT / "eval/trashnet.json").write_text(json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
