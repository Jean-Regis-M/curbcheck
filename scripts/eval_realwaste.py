"""v1 cross-dataset stress test on RealWaste (landfill photos, never seen by the v1 head) at the FIXED threshold
chosen on TACO validation. Ground truth is only defined where all cities agree at material level:
Cardboard/Glass/Metal/Paper -> accept; Food Organics/Misc Trash/Textile/Vegetation -> not accept.
Plastic is excluded (bottles accepted, bags rejected, so a material label gives no verdict).
Data: HuggingFace mirror shahzaibvohra/realwaste parquet shards in data/raw/realwaste/ (label = filename prefix)."""
import io
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from PIL import Image

from curbcheck.decision import decide
from curbcheck.model import ClipHeadClassifier
from curbcheck.rules import load_city

ACCEPT = {"Cardboard", "Glass", "Metal", "Paper"}
NOT_ACCEPT = {"Food Organics", "Miscellaneous Trash", "Textile Trash", "Vegetation"}
PER_CLASS = 150
CITIES = ["seattle", "washington_dc", "new_york"]


def main():
    import pyarrow.parquet as pq
    items = []
    for shard in sorted((ROOT / "data/raw/realwaste").glob("p*.parquet")):
        for rec in pq.read_table(shard, columns=["image"]).column("image").to_pylist():
            items.append((re.sub(r"_\d+\.\w+$", "", rec["path"]), rec["bytes"]))
    clf = ClipHeadClassifier(ROOT / "models/head_v1.npz")
    rng = np.random.default_rng(0)
    probs, truth, cls = [], [], []
    for cname in sorted(ACCEPT | NOT_ACCEPT):
        pool = [b for c, b in items if c == cname]
        for k in rng.choice(len(pool), min(PER_CLASS, len(pool)), replace=False):
            probs.append(clf.predict(Image.open(io.BytesIO(pool[k]))))
            truth.append("accept" if cname in ACCEPT else "other")
            cls.append(cname)
        print(cname, len(pool), flush=True)
    truth, cls = np.array(truth), np.array(cls)
    out = {"threshold": clf.threshold, "per_class_sampled": PER_CLASS, "n": len(truth), "cities": {}}
    non = truth == "other"
    for cid in CITIES:
        city = load_city(cid)
        ds = [decide(p, city, threshold=clf.threshold) for p in probs]
        ans = np.array([d.verdict for d in ds])
        forced = np.array(["accept" if d.p_accept >= d.p_reject else "reject" for d in ds])

        def far(a, idx):
            return float(((a[idx] == "accept") & non[idx]).sum() / max(non[idx].sum(), 1))
        allidx = np.arange(len(truth))
        boots = [far(ans, rng.choice(allidx, len(allidx))) for _ in range(500)]
        out["cities"][cid] = {
            "coverage": float((ans != "not_sure").mean()),
            "false_accept_rate": far(ans, allidx), "far_ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
            "no_abstention_false_accept_rate": far(forced, allidx),
            "missed_recyclable_rate": float(((ans == "reject") & ~non).sum() / max((~non).sum(), 1)),
            "no_abstention_missed_recyclable_rate": float(((forced == "reject") & ~non).sum() / max((~non).sum(), 1)),
            "false_accept_by_class": {c: float(((ans == "accept") & (cls == c)).sum() / (cls == c).sum()) for c in sorted(NOT_ACCEPT)},
        }
    (ROOT / "eval/realwaste.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
