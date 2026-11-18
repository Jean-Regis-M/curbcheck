"""What does the shipped model do with the three item types it was never trained on as separate classes?

TACO has 2 battery, 3 greasy-pizza-box and 5 food-waste crops. They were excluded from training (too few), so they are an unseen,
tiny smoke test: how many does the shipped model wrongly tell someone to recycle ("accept"), in each city?
RealWaste "Food Organics" photos were used for training the food-waste class, so they are not used here.
Usage: python scripts/hazard_check.py -> eval/hazard_check.json
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import run_methods

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from curbcheck.head import probs_from_features
from curbcheck.rules import list_cities, load_city

HAZARD = ["battery", "pizza_box_greasy", "food_waste"]


def main():
    head = np.load(ROOT / "models/head.npz", allow_pickle=False)
    classes, thr = [str(c) for c in head["classes"]], float(head["threshold"])
    rows = json.loads((ROOT / "data/raw/taco/crops.json").read_text("utf-8"))
    X = np.load(ROOT / "data/cache/taco_clip_b32.npy")
    items = np.array([r["item"] for r in rows])
    P = probs_from_features(X, head)
    out = {"threshold": thr, "note": "tiny sets, a smoke test and not evidence", "items": {}}
    for h in HAZARD:
        m = items == h
        per_city = {}
        for cid in list_cities():
            ans, conf = run_methods(P[m], classes, load_city(cid))["B_verdict_mass"]
            verdict = np.where(conf >= thr, ans, "not_sure")
            per_city[cid] = dict(Counter(verdict.tolist()))
        total = Counter()
        for v in per_city.values():
            total.update(v)
        out["items"][h] = {"crops": int(m.sum()), "verdicts_over_all_city_answers": dict(total),
                           "share_wrongly_accepted": total["accept"] / max(sum(total.values()), 1), "per_city": per_city}
    (ROOT / "eval/hazard_check.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for h, v in out["items"].items():
        print(h, v["crops"], "crops;", v["verdicts_over_all_city_answers"], "wrongly accepted:", round(v["share_wrongly_accepted"], 3))


if __name__ == "__main__":
    main()
