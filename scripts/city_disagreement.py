"""How often does the same photo get a different answer in different cities?  This is the premise of the product, measured.

For every photo in TrashNet, RealWaste and the held-out TACO crops, the shipped model's answer (accept, reject or not sure) is
computed for each of the seven cities. We report the share of photos where the cities do not all agree, and the share where one
city says "recycle it" and another says "not recyclable" (a hard conflict). Plastic photos are included: this does not need
ground truth.   Usage: python scripts/city_disagreement.py -> eval/city_disagreement.json
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import load, run_methods, split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from curbcheck.head import probs_from_features
from curbcheck.rules import list_cities, load_city


def verdict_matrix(X, head):
    classes, thr = [str(c) for c in head["classes"]], float(head["threshold"])
    P = probs_from_features(X, head)
    cols = []
    for cid in list_cities():
        ans, conf = run_methods(P, classes, load_city(cid))["B_verdict_mass"]
        cols.append(np.where(conf >= thr, ans, "not_sure"))
    return np.stack(cols, 1)


def summarise(M):
    differ = np.array([len(set(r)) > 1 for r in M])
    hard = np.array([("accept" in r) and ("reject" in r) for r in M])
    return {"photos": len(M), "cities_not_all_agree": float(differ.mean()), "accept_in_one_reject_in_another": float(hard.mean())}


def main():
    head = np.load(ROOT / "models/head.npz", allow_pickle=False)
    rows, Xt, _, _ = load()
    test = split(rows) == "test"
    Xn = np.load(ROOT / "data/cache/trashnet_clip_b32.npy")
    Xr = np.load(ROOT / "data/cache/realwaste_clip_b32.npy")
    out = {"cities": len(list_cities()), "TACO_test": summarise(verdict_matrix(Xt[test], head)),
           "TrashNet": summarise(verdict_matrix(Xn, head)), "RealWaste": summarise(verdict_matrix(Xr, head))}
    (ROOT / "eval/city_disagreement.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for k, v in out.items():
        if isinstance(v, dict):
            print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items()})


if __name__ == "__main__":
    main()
