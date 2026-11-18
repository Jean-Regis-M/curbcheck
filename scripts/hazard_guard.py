"""Can a zero-shot guard catch the three item types the trained head cannot recognise (batteries, greasy or food-soiled
pizza boxes, food waste) and force "not sure" instead of a confident wrong answer?

The guard uses CLIP's text side only: the probability mass that zero-shot CLIP puts on the three hazard prompts, out of all 16
item prompts. If it reaches a threshold the answer becomes "not sure". The threshold is picked so that at most 5% of ordinary TACO
crops (no hazard) are flagged. Positives are tiny for batteries (2) and pizza boxes (3): this is a smoke test for them, not evidence.
Food waste has a real positive set (5 TACO crops, 411 RealWaste "Food Organics" photos).
Usage: python scripts/hazard_guard.py -> eval/hazard_guard.json
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.special import softmax

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import metrics, run_methods, zero_shot_logits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from curbcheck.rules import list_cities, load_city
from curbcheck.taxonomy import ITEMS

HAZARD = ["battery", "pizza_box_greasy", "food_waste"]
ALL = list(ITEMS)
MAX_NORMAL_FLAG_RATE = 0.05


def hazard_mass(X):
    p = softmax(zero_shot_logits(X, ALL), axis=1)
    return p[:, [ALL.index(h) for h in HAZARD]].sum(1), p


def main():
    # read every TACO crop, including the classes too small to train on (batteries, pizza boxes, food waste)
    all_rows = json.loads((ROOT / "data/raw/taco/crops.json").read_text("utf-8"))
    Xall = np.load(ROOT / "data/cache/taco_clip_b32.npy")
    items = np.array([r["item"] for r in all_rows])
    Xn = np.load(ROOT / "data/cache/trashnet_clip_b32.npy")
    ln = np.array(json.load(open(ROOT / "data/cache/trashnet_labels.json")))
    Xr = np.load(ROOT / "data/cache/realwaste_clip_b32.npy")
    lr = np.array(json.load(open(ROOT / "data/cache/realwaste_labels.json")))
    mt, _ = hazard_mass(Xall)
    mn, _ = hazard_mass(Xn)
    mr, _ = hazard_mass(Xr)
    normal_t = ~np.isin(items, HAZARD)
    tau = float(np.quantile(mt[normal_t], 1 - MAX_NORMAL_FLAG_RATE))
    rate = lambda m, mask: float((m[mask] >= tau).mean()) if mask.any() else None
    out = {"threshold": tau, "target_max_flag_rate_on_ordinary_taco": MAX_NORMAL_FLAG_RATE,
           "recall": {f"battery (TACO, n={(items == 'battery').sum()})": rate(mt, items == "battery"),
                      f"greasy pizza box (TACO, n={(items == 'pizza_box_greasy').sum()})": rate(mt, items == "pizza_box_greasy"),
                      f"food waste (TACO, n={(items == 'food_waste').sum()})": rate(mt, items == "food_waste"),
                      f"food organics (RealWaste, n={(lr == 'Food Organics').sum()})": rate(mr, lr == "Food Organics")},
           "false_trigger": {"ordinary TACO crops": rate(mt, normal_t), "TrashNet cardboard/glass/metal/paper": rate(mn, np.isin(ln, ["cardboard", "glass", "metal", "paper"])),
                             "TrashNet trash": rate(mn, ln == "trash"), "RealWaste cardboard/glass/metal/paper": rate(mr, np.isin(lr, ["Cardboard", "Glass", "Metal", "Paper"]))}}
    # effect on the shipped v1 head on TrashNet: items flagged by the guard become "not sure"
    h = np.load(ROOT / "models/head_v1.npz", allow_pickle=False)
    classes, thr = [str(c) for c in h["classes"]], float(h["threshold"])
    P = softmax((Xn @ h["W"].T + h["b"]) / float(h["T"]), axis=1)
    keep = ln != "plastic"
    truth = np.where(np.isin(ln, ["cardboard", "glass", "metal", "paper"]), "accept", "other")[keep]
    eff = {}
    for cid in list_cities():
        ans, conf = run_methods(P[keep], classes, load_city(cid))["B_verdict_mass"]
        cov0, far0, miss0 = metrics(ans, conf, truth, thr)
        conf_g = np.where(mn[keep] >= tau, 0.0, conf)
        cov1, far1, miss1 = metrics(ans, conf_g, truth, thr)
        eff[cid] = {"without_guard": {"coverage": float(cov0), "false_accept": float(far0), "missed": float(miss0)},
                    "with_guard": {"coverage": float(cov1), "false_accept": float(far1), "missed": float(miss1)}}
    out["effect_on_v1_head_on_trashnet"] = eff
    (ROOT / "eval/hazard_guard.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("threshold", round(tau, 3))
    for k, v in out["recall"].items():
        print("recall", k, v)
    for k, v in out["false_trigger"].items():
        print("false trigger", k, round(v, 3))
    for cid in ("seattle", "austin"):
        print(cid, {k: {a: round(b, 3) for a, b in v.items()} for k, v in eff[cid].items()})


if __name__ == "__main__":
    main()
