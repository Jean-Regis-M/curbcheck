"""Train the shipped classifier head and choose the abstention threshold on the validation split only.
Writes models/head_v1.npz and eval/fixed_threshold.json (test metrics at the pre-chosen threshold)."""
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.special import softmax
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import CITIES, SEED, fit_temperature, load, metrics, run_methods, split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from curbcheck.rules import load_city

TARGET_VAL_COVERAGE = 0.7
NAME = os.environ.get("CURBCHECK_HEAD", "head_v1")  # head_web = trained on in-browser features
SUFFIX = "" if NAME == "head_v1" else "_" + NAME.split("_")[-1]


def main():
    rows, X, classes, _ = load()
    part = split(rows)
    y = np.array([classes.index(r["item"]) for r in rows])
    tr, va, te = part == "train", part == "val", part == "test"
    clf = LogisticRegression(C=10, max_iter=3000).fit(X[tr], y[tr])
    lg = clf.decision_function(X)
    T = fit_temperature(lg[va], y[va])
    P = softmax(lg / T, axis=1)
    confs = []
    for cid in CITIES:
        city = load_city(cid)
        _, conf = run_methods(P, classes, city)["B_verdict_mass"]
        confs.append(conf[va])
    pooled = np.concatenate(confs)
    thr = float(np.quantile(pooled, 1 - TARGET_VAL_COVERAGE))
    np.savez(ROOT / "models" / f"{NAME}.npz", W=clf.coef_, b=clf.intercept_, T=T, threshold=thr,
             classes=np.array(classes), seed=SEED)
    out = {"threshold_chosen_on_val": thr, "temperature": T, "test": {}}
    for cid in CITIES:
        city = load_city(cid)
        truth = np.array([city.rules[classes[k]].verdict for k in y])
        ans, conf = run_methods(P, classes, city)["B_verdict_mass"]
        cov, far, miss = metrics(ans[te], conf[te], truth[te], thr)
        cov_all, far_all, miss_all = metrics(ans[te], np.ones(te.sum()), truth[te], 0.0)
        out["test"][cid] = {"coverage": float(cov), "false_accept_rate": float(far), "missed_recyclable_rate": float(miss),
                            "no_abstention": {"coverage": float(cov_all), "false_accept_rate": float(far_all),
                                              "missed_recyclable_rate": float(miss_all)}}
    (ROOT / f"eval/fixed_threshold{SUFFIX}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
