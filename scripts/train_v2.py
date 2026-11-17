"""v2 head: train on TACO train + RealWaste train (weak material labels), calibrate and choose the threshold
on TACO val + RealWaste val, report on held-out TACO test and held-out RealWaste test, v1 vs v2.
Writes models/head_v2.npz and eval/v2.json. Does not overwrite models/head_v1.npz."""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.special import softmax
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import fit_temperature, load, metrics, run_methods, split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from curbcheck.rules import load_city

CITIES = ["seattle", "washington_dc", "new_york"]
RW_ITEM = {"Cardboard": "cardboard_box", "Paper": "paper_clean", "Glass": "glass_bottle_jar",
           "Food Organics": "food_waste", "Vegetation": "other_trash", "Textile Trash": "other_trash",
           "Miscellaneous Trash": "other_trash"}  # Metal resolved below; Plastic excluded
ACCEPT = {"Cardboard", "Glass", "Metal", "Paper"}
METAL_ITEMS = ["aluminum_can", "steel_can", "aluminum_foil"]
TARGET_COV = 0.7


def probs_v1(X):
    h = np.load(ROOT / "models/head_v1.npz", allow_pickle=False)
    return softmax((X @ h["W"].T + h["b"]) / float(h["T"]), axis=1), [str(c) for c in h["classes"]], float(h["threshold"])


def main():
    rows, X, tclasses, _ = load()
    tpart = split(rows)
    timg = np.array([r["image_id"] for r in rows])
    tlab = np.array([r["item"] for r in rows])
    F = np.load(ROOT / "data/cache/realwaste_clip_b32.npy")
    L = np.array(json.load(open(ROOT / "data/cache/realwaste_labels.json")))
    rng = np.random.default_rng(0)
    rpart = np.empty(len(L), dtype=object)
    for c in np.unique(L):
        idx = rng.permutation(np.where(L == c)[0])
        n = len(idx)
        rpart[idx[:int(.5 * n)]], rpart[idx[int(.5 * n):int(.75 * n)]], rpart[idx[int(.75 * n):]] = "train", "val", "test"
    keep = L != "Plastic"
    # weak item labels for RealWaste; metal resolved with the v1 model restricted to metal items
    P1, c1, thr1 = probs_v1(F)
    mi = [c1.index(m) for m in METAL_ITEMS]
    ritem = np.array([RW_ITEM.get(c, "") for c in L], dtype=object)
    for i in np.where(L == "Metal")[0]:
        ritem[i] = METAL_ITEMS[int(np.argmax(P1[i, mi]))]
    classes = sorted(set(tclasses) | {"food_waste"})
    ci = {c: k for k, c in enumerate(classes)}
    use_r = keep & (ritem != "")
    Xtr = np.concatenate([X[tpart == "train"], F[use_r & (rpart == "train")]])
    ytr = np.array([ci[c] for c in tlab[tpart == "train"]] + [ci[c] for c in ritem[use_r & (rpart == "train")]])
    Xva = np.concatenate([X[tpart == "val"], F[use_r & (rpart == "val")]])
    yva = np.array([ci[c] for c in tlab[tpart == "val"]] + [ci[c] for c in ritem[use_r & (rpart == "val")]])
    clf = LogisticRegression(C=10, max_iter=4000).fit(Xtr, ytr)
    T = fit_temperature(clf.decision_function(Xva), yva)
    sm = lambda Z: softmax(clf.decision_function(Z) / T, axis=1)
    # threshold: pooled verdict-mass confidence on the (TACO val + RW val) pool, 70% target coverage
    confs = [run_methods(sm(Xva), classes, load_city(c))["B_verdict_mass"][1] for c in CITIES]
    thr = float(np.quantile(np.concatenate(confs), 1 - TARGET_COV))
    np.savez(ROOT / "models/head_v2.npz", W=clf.coef_, b=clf.intercept_, T=T, threshold=thr, classes=np.array(classes))
    out = {"threshold_v2": thr, "threshold_v1": thr1, "temperature": T, "classes": classes,
           "n_train": len(ytr), "n_val": len(yva), "taco_test": {}, "realwaste_test": {}}

    def boot(fn, n, groups=None, B=300):
        r = np.random.default_rng(5)
        vals = []
        for _ in range(B):
            if groups is None:
                idx = r.integers(0, n, n)
            else:
                g = np.unique(groups)
                idx = np.concatenate([np.where(groups == k)[0] for k in r.choice(g, len(g))])
            vals.append(fn(idx))
        return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]

    def report(P, cls, thr_, truth, groups):
        res = {}
        for cid in CITIES:
            city = load_city(cid)
            tr = truth(city)
            ans, conf = run_methods(P, cls, city)["B_verdict_mass"]
            cov, far, miss = metrics(ans, conf, tr, thr_)
            _, farf, missf = metrics(ans, np.ones(len(ans)), tr, 0.0)
            res[cid] = {"coverage": float(cov), "false_accept_rate": float(far), "missed_recyclable_rate": float(miss),
                        "forced_false_accept_rate": float(farf), "forced_missed_recyclable_rate": float(missf),
                        "far_ci95": boot(lambda i: metrics(ans[i], conf[i], tr[i], thr_)[1], len(ans), groups),
                        "missed_ci95": boot(lambda i: metrics(ans[i], conf[i], tr[i], thr_)[2], len(ans), groups)}
        return res

    te_t = tpart == "test"
    for name, P_all, cls, thr_ in (("v1", None, c1, thr1), ("v2", None, classes, thr)):
        if name == "v1":
            Pt = probs_v1(X[te_t])[0]
            PtR = P1[use_r & (rpart == "test")]
        else:
            Pt, PtR = sm(X[te_t]), sm(F[use_r & (rpart == "test")])
        cl = c1 if name == "v1" else classes
        out["taco_test"][name] = report(Pt, cl, thr_, lambda city: np.array([city.rules[c].verdict for c in tlab[te_t]]), timg[te_t])
        rl = L[use_r & (rpart == "test")]
        out["realwaste_test"][name] = report(PtR, cl, thr_, lambda city: np.where(np.isin(rl, list(ACCEPT)), "accept", "other"), None)
    out["n_test"] = {"taco": int(te_t.sum()), "realwaste": int((use_r & (rpart == "test")).sum())}
    (ROOT / "eval/v2.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for d in ("taco_test", "realwaste_test"):
        for v in ("v1", "v2"):
            for c, r in out[d][v].items():
                print(d, v, c, {k: round(x, 3) for k, x in r.items() if not k.endswith("ci95")})


if __name__ == "__main__":
    main()
