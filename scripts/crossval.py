"""Repeated grouped-split evaluation with calibration error and risk-controlled abstention.

1. R random splits of TACO *photos* (60/20/20), threshold chosen on validation only (as in train_head.py);
   reports mean and standard deviation of false-accept rate, coverage and accept precision per city, using every crop
   as a test item across the repeats (not just one 306-crop split).
2. Calibration: expected calibration error (15 bins) of the item head before and after temperature scaling.
3. Risk control (fixed-sequence testing with one-sided Clopper-Pearson bounds): choose the lowest threshold whose
   validation false-accept rate is provably <= alpha at confidence 1 - delta, then check it on the held-out test part.
Usage: python scripts/crossval.py   -> eval/crossval.json"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import beta
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import fit_temperature, load, run_methods

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from curbcheck.rules import list_cities, load_city

CITIES = list_cities()
R = 20
ALPHAS = (0.02, 0.05, 0.10)
DELTA = 0.10
GRID = np.round(np.arange(0.99, 0.49, -0.01), 2)  # most conservative first
TARGET_COV = 0.7


def split_seed(rows, seed):
    ids = sorted({r["image_id"] for r in rows})
    rng = np.random.default_rng(seed)
    rng.shuffle(ids)
    n = len(ids)
    part = {i: ("train" if k < 0.6 * n else "val" if k < 0.8 * n else "test") for k, i in enumerate(ids)}
    return np.array([part[r["image_id"]] for r in rows])


def ece(P, y, bins=15):
    conf, pred = P.max(1), P.argmax(1)
    acc = (pred == y).astype(float)
    edges = np.linspace(0, 1, bins + 1)
    out = 0.0
    for lo, hi in itertools.pairwise(edges):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            out += m.mean() * abs(acc[m].mean() - conf[m].mean())
    return float(out)


def cp_upper(k, n, conf):
    return 1.0 if n == 0 else float(beta.ppf(conf, k + 1, n - k)) if k < n else 1.0


def softmax(Z):
    Z = Z - Z.max(1, keepdims=True)
    E = np.exp(Z)
    return E / E.sum(1, keepdims=True)


def main():
    rows, X, classes, _ = load()
    y = np.array([classes.index(r["item"]) for r in rows])
    truth = {c: np.array([load_city(c).rules[classes[k]].verdict for k in y]) for c in CITIES}
    acc = {c: {"far": [], "forced": [], "cov": [], "prec": [], "miss": []} for c in CITIES}
    ece_raw, ece_cal, rc = [], [], {a: {"far": [], "cov": [], "viol": [], "found": []} for a in ALPHAS}
    for seed in range(R):
        part = split_seed(rows, 1000 + seed)
        tr, va, te = part == "train", part == "val", part == "test"
        clf = LogisticRegression(C=10, max_iter=3000).fit(X[tr], y[tr])
        Z = clf.decision_function(X)
        T = fit_temperature(Z[va], y[va])
        P = softmax(Z / T)
        ece_raw.append(ece(softmax(Z)[te], y[te]))
        ece_cal.append(ece(P[te], y[te]))
        res = {c: run_methods(P, classes, load_city(c))["B_verdict_mass"] for c in CITIES}
        thr = float(np.quantile(np.concatenate([res[c][1][va] for c in CITIES]), 1 - TARGET_COV))
        for c in CITIES:
            ans, conf = res[c]
            non, rec = truth[c] != "accept", truth[c] == "accept"
            answered = conf >= thr
            fa = answered & (ans == "accept") & non
            aa = answered & (ans == "accept")
            forced_fa = (ans == "accept") & non
            acc[c]["far"].append(fa[te].sum() / max(non[te].sum(), 1))
            acc[c]["forced"].append(forced_fa[te].sum() / max(non[te].sum(), 1))
            acc[c]["cov"].append(answered[te].mean())
            acc[c]["prec"].append(1 - fa[te].sum() / max(aa[te].sum(), 1))
            acc[c]["miss"].append((answered & (ans == "reject") & rec)[te].sum() / max(rec[te].sum(), 1))
            for a in ALPHAS:  # fixed-sequence test from the most conservative threshold downwards
                chosen = None
                for lam in GRID:
                    k = int(((conf >= lam) & (ans == "accept") & non)[va].sum())
                    if cp_upper(k, int(non[va].sum()), 1 - DELTA) <= a:
                        chosen = lam
                    else:
                        break
                if chosen is None:
                    rc[a]["found"].append(0)
                    continue
                rc[a]["found"].append(1)
                ok = (conf >= chosen) & (ans == "accept") & non
                rc[a]["far"].append(ok[te].sum() / max(non[te].sum(), 1))
                rc[a]["cov"].append(((conf >= chosen) & (ans != "not_sure"))[te].mean())
                rc[a]["viol"].append(float(ok[te].sum() / max(non[te].sum(), 1) > a))
    ms = lambda v: {"mean": float(np.mean(v)), "sd": float(np.std(v))}
    out = {"repeats": R, "n_crops": len(rows), "ece_before_temperature": ms(ece_raw), "ece_after_temperature": ms(ece_cal),
           "cities": {c: {k: ms(v) for k, v in d.items()} for c, d in acc.items()},
           "risk_control": {str(a): {"delta": DELTA, "threshold_found_share": float(np.mean(d["found"])),
                                      "test_far": ms(d["far"]) if d["far"] else None, "coverage": ms(d["cov"]) if d["cov"] else None,
                                      "share_of_runs_with_test_far_above_alpha": float(np.mean(d["viol"])) if d["viol"] else None}
                            for a, d in rc.items()}}
    (ROOT / "eval/crossval.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("ece_before_temperature", "ece_after_temperature")}))
    for c, d in out["cities"].items():
        print(c.ljust(14), {k: f"{v['mean']*100:.1f}±{v['sd']*100:.1f}" for k, v in d.items()})
    for a, d in out["risk_control"].items():
        print("alpha", a, {k: (round(v["mean"], 3) if isinstance(v, dict) else (round(v, 3) if v is not None else None)) for k, v in d.items() if k != "delta"})


if __name__ == "__main__":
    main()
