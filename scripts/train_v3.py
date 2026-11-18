"""v3: multi-domain training (TACO litter + TrashNet studio + RealWaste landfill) with an optional zero-shot blend, judged
by leave-one-dataset-out tests, the honest estimate of behaviour on a photo domain the model has never seen.

  A: train TACO + RealWaste -> test TrashNet (unseen)
  B: train TACO + TrashNet  -> test RealWaste (unseen)
  F: train on all three     -> test the held-out part of each dataset (in-domain)

Weak material labels as in train_v2.py; plastic is excluded; metal is resolved by the v1 head. Temperature and threshold are
chosen on validation data of the training datasets only. Writes eval/v3.json.
Usage: python scripts/train_v3.py
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.special import softmax
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import (
    fit_temperature,
    load,
    metrics,
    run_methods,
    split,
    zero_shot_logits,
    zero_shot_text,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from curbcheck.rules import list_cities, load_city

CITIES = list_cities()
TN_ITEM = {"cardboard": "cardboard_box", "glass": "glass_bottle_jar", "paper": "paper_clean", "trash": "other_trash"}
RW_ITEM = {"Cardboard": "cardboard_box", "Paper": "paper_clean", "Glass": "glass_bottle_jar", "Food Organics": "food_waste",
           "Vegetation": "other_trash", "Textile Trash": "other_trash", "Miscellaneous Trash": "other_trash"}
ACCEPT_TN = ["cardboard", "glass", "metal", "paper"]
ACCEPT_RW = ["Cardboard", "Glass", "Metal", "Paper"]
METAL = ["aluminum_can", "steel_can", "aluminum_foil"]
LAMBDAS = (2.0,)
CLASS_WEIGHTS = (None,)
TARGET_COVS = (0.5, 0.55, 0.6, 0.65, 0.7)
MODE = os.environ.get("CURBCHECK_FEATURES_SET", "py")  # "web" = features computed by the in-browser pipeline
SUF = "" if MODE == "py" else "_web"
ZS_SCALE = 0.1  # zero-shot logits are 100 * cosine; bring them to the head's logit range


def v1_probs(X):
    h = np.load(ROOT / "models/head_v1.npz", allow_pickle=False)
    return softmax((X @ h["W"].T + h["b"]) / float(h["T"]), axis=1), [str(c) for c in h["classes"]]


def weak_items(labels, P1, mapping, metal_name, c1):
    item = np.array([mapping.get(c, "") for c in labels], dtype=object)
    mi = [c1.index(m) for m in METAL]
    for i in np.where(labels == metal_name)[0]:
        item[i] = METAL[int(np.argmax(P1[i, mi]))]
    return item


def stratified_parts(labels, seed=0):
    rng = np.random.default_rng(seed)
    out = np.empty(len(labels), dtype=object)
    for c in np.unique(labels):
        idx = rng.permutation(np.where(labels == c)[0])
        n = len(idx)
        out[idx[:int(.5 * n)]], out[idx[int(.5 * n):int(.75 * n)]], out[idx[int(.75 * n):]] = "train", "val", "test"
    return out


def evaluate_probs(P, classes, truth_fn, thr):
    out = {}
    for cid in CITIES:
        city = load_city(cid)
        ans, conf = run_methods(P, classes, city)["B_verdict_mass"]
        tr = truth_fn(city)
        cov, far, miss = metrics(ans, conf, tr, thr)
        _, farf, missf = metrics(ans, np.ones(len(ans)), tr, 0.0)
        out[cid] = {"coverage": float(cov), "false_accept_rate": float(far), "missed_recyclable_rate": float(miss),
                    "forced_false_accept_rate": float(farf), "forced_missed_recyclable_rate": float(missf)}
    return out


def fit(Xtr, ytr, Ztr, Xva, yva, Zva, lam, cw=None):
    clf = LogisticRegression(C=10, max_iter=4000, class_weight=cw).fit(Xtr, ytr)

    def logits(X, Z):
        full = np.full((len(X), Z.shape[1]), -30.0)  # a class absent from the training data gets a very low logit
        full[:, clf.classes_] = clf.decision_function(X)
        return full + lam * Z

    T = fit_temperature(logits(Xva, Zva), yva)
    return clf, T, (lambda X, Z: softmax(logits(X, Z) / T, axis=1))


def run():
    rows, Xt, tclasses, _ = load()
    tpart = split(rows)
    classes = sorted(set(tclasses) | {"food_waste"})
    ci = {c: k for k, c in enumerate(classes)}
    t_item = np.array([r["item"] for r in rows])
    Xn = np.load(ROOT / "data/cache/trashnet_clip_b32.npy")
    ln = np.array(json.load(open(ROOT / "data/cache/trashnet_labels.json")))
    Xr = np.load(ROOT / "data/cache/realwaste_clip_b32.npy")
    lr = np.array(json.load(open(ROOT / "data/cache/realwaste_labels.json")))
    P1n, c1 = v1_probs(Xn)  # weak-label resolution always uses the PyTorch v1 head on PyTorch features
    P1r, _ = v1_probs(Xr)
    n_item, r_item = weak_items(ln, P1n, TN_ITEM, "metal", c1), weak_items(lr, P1r, RW_ITEM, "Metal", c1)
    npart, rpart = stratified_parts(ln), stratified_parts(lr)
    text = zero_shot_text(classes)
    if MODE == "web":
        from collections import Counter
        all_rows = json.loads((ROOT / "data/raw/taco/crops.json").read_text("utf-8"))
        counts = Counter(r["item"] for r in all_rows)
        keep = np.array([counts[r["item"]] >= 25 for r in all_rows])  # same classes as evaluate.load()
        Xt = np.load(ROOT / "data/cache/taco_web_q8.npy")[keep]
        Xn = np.load(ROOT / "data/cache/trashnet_web_q8.npy")
        Xr = np.load(ROOT / "data/cache/realwaste_web_q8.npy")
    zt, zn, zr = (zero_shot_logits(X, classes, text) * ZS_SCALE for X in (Xt, Xn, Xr))
    ok_n, ok_r = (n_item != "") & (ln != "plastic"), (r_item != "") & (lr != "Plastic")
    truth_n = np.where(np.isin(ln, ACCEPT_TN), "accept", "other")
    truth_r = np.where(np.isin(lr, ACCEPT_RW), "accept", "other")
    tr_t, va_t, te_t = tpart == "train", tpart == "val", tpart == "test"

    def y(items, mask):
        return np.array([ci[c] for c in items[mask]])

    def threshold(prob_sets, tc):
        confs = [run_methods(P, classes, load_city(c))["B_verdict_mass"][1] for P in prob_sets for c in CITIES]
        return float(np.quantile(np.concatenate(confs), 1 - tc))

    out = {"classes": classes, "lambdas": list(LAMBDAS), "A_train_TACO_RealWaste_test_TrashNet": {},
           "B_train_TACO_TrashNet_test_RealWaste": {}, "F_all_three_in_domain": {}}
    configs = [(lam, cw, tc) for lam in LAMBDAS for cw in CLASS_WEIGHTS for tc in TARGET_COVS]
    for lam, cw, tc in configs:
        key = f"zs{lam}|{cw}|cov{tc}"
        # A
        r_tr, r_va = ok_r & (rpart != "test"), ok_r & (rpart == "test")
        clf, T, prob = fit(np.concatenate([Xt[tr_t], Xr[r_tr]]), np.concatenate([y(t_item, tr_t), y(r_item, r_tr)]), np.concatenate([zt[tr_t], zr[r_tr]]),
                           np.concatenate([Xt[va_t], Xr[r_va]]), np.concatenate([y(t_item, va_t), y(r_item, r_va)]), np.concatenate([zt[va_t], zr[r_va]]), lam, cw)
        thr = threshold([prob(np.concatenate([Xt[va_t], Xr[r_va]]), np.concatenate([zt[va_t], zr[r_va]]))], tc)
        out["A_train_TACO_RealWaste_test_TrashNet"][key] = {
            "threshold": thr, "cities": evaluate_probs(prob(Xn[ok_n], zn[ok_n]), classes, lambda c: truth_n[ok_n], thr)}
        # B
        n_tr, n_va = ok_n & (npart != "test"), ok_n & (npart == "test")
        clf, T, prob = fit(np.concatenate([Xt[tr_t], Xn[n_tr]]), np.concatenate([y(t_item, tr_t), y(n_item, n_tr)]), np.concatenate([zt[tr_t], zn[n_tr]]),
                           np.concatenate([Xt[va_t], Xn[n_va]]), np.concatenate([y(t_item, va_t), y(n_item, n_va)]), np.concatenate([zt[va_t], zn[n_va]]), lam, cw)
        thr = threshold([prob(np.concatenate([Xt[va_t], Xn[n_va]]), np.concatenate([zt[va_t], zn[n_va]]))], tc)
        out["B_train_TACO_TrashNet_test_RealWaste"][key] = {
            "threshold": thr, "cities": evaluate_probs(prob(Xr[ok_r], zr[ok_r]), classes, lambda c: truth_r[ok_r], thr)}
        # F
        parts = {"train": [(Xt[tr_t], y(t_item, tr_t), zt[tr_t]), (Xn[ok_n & (npart == "train")], y(n_item, ok_n & (npart == "train")), zn[ok_n & (npart == "train")]),
                           (Xr[ok_r & (rpart == "train")], y(r_item, ok_r & (rpart == "train")), zr[ok_r & (rpart == "train")])],
                 "val": [(Xt[va_t], y(t_item, va_t), zt[va_t]), (Xn[ok_n & (npart == "val")], y(n_item, ok_n & (npart == "val")), zn[ok_n & (npart == "val")]),
                         (Xr[ok_r & (rpart == "val")], y(r_item, ok_r & (rpart == "val")), zr[ok_r & (rpart == "val")])]}
        cat = {k: [np.concatenate([b[i] for b in v]) for i in range(3)] for k, v in parts.items()}
        clf, T, prob = fit(*cat["train"], *cat["val"], lam, cw)
        thr = threshold([prob(b[0], b[2]) for b in parts["val"]], tc)
        m_n, m_r = ok_n & (npart == "test"), ok_r & (rpart == "test")
        out["F_all_three_in_domain"][key] = {
            "threshold": thr, "temperature": T,
            "TACO_test": evaluate_probs(prob(Xt[te_t], zt[te_t]), classes, lambda c: np.array([c.rules[x].verdict for x in t_item[te_t]]), thr),
            "TrashNet_test": evaluate_probs(prob(Xn[m_n], zn[m_n]), classes, lambda c: truth_n[m_n], thr),
            "RealWaste_test": evaluate_probs(prob(Xr[m_r], zr[m_r]), classes, lambda c: truth_r[m_r], thr)}
        np.savez(ROOT / f"models/cand_v3{SUF}_{key.replace('|', '_')}.npz", W=clf.coef_, b=clf.intercept_, T=T, threshold=thr, classes=np.array(classes), zs_lambda=lam)
        print(key, "done", flush=True)
    h1 = np.load(ROOT / ("models/head_v1.npz" if MODE == "py" else "models/head_web_v1.npz"), allow_pickle=False)
    thr1 = float(h1["threshold"])
    base = {}
    for name, X, keep, truth in (("TrashNet", Xn, ok_n, truth_n), ("RealWaste", Xr, ok_r, truth_r)):
        P1 = softmax((X[keep] @ h1["W"].T + h1["b"]) / float(h1["T"]), axis=1)
        base[name] = evaluate_probs(P1, c1, lambda c, t=truth[keep]: t, thr1)
    out["v1_baseline_same_sets"] = base
    np.save(ROOT / f"models/zs_text_v3{SUF}.npy", text)
    (ROOT / f"eval/v3{SUF}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for key in ("A_train_TACO_RealWaste_test_TrashNet", "B_train_TACO_TrashNet_test_RealWaste"):
        for lam, r in out[key].items():
            c = r["cities"]["seattle"]
            print(key[:1], "lam", lam, {k: round(v, 3) for k, v in c.items()})


if __name__ == "__main__":
    run()
