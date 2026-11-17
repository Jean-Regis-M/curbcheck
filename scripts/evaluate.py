"""Evaluate item classifier + city-rule decision on TACO crops, split by source photo.
Compares (A) abstaining on item confidence vs (B) abstaining on city-verdict probability mass.
Writes eval/results.json and eval/far_vs_coverage.png. Run: python scripts/evaluate.py"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import open_clip
import torch
from scipy.optimize import minimize_scalar
from scipy.special import softmax
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from curbcheck.rules import load_city
from curbcheck.taxonomy import ITEMS

MIN_CROPS = 25
SEED = 0
CITIES = ["seattle", "washington_dc"]
TARGETS = [0.5, 0.7, 0.9]


def load():
    rows = json.loads((ROOT / "data/raw/taco/crops.json").read_text("utf-8"))
    X = np.load(ROOT / "data/cache" / os.environ.get("CURBCHECK_FEATURES", "taco_clip_b32.npy"))
    counts = Counter(r["item"] for r in rows)
    classes = sorted(k for k, v in counts.items() if v >= MIN_CROPS)
    keep = [i for i, r in enumerate(rows) if r["item"] in classes]
    return [rows[i] for i in keep], X[keep], classes, {k: v for k, v in counts.items() if k not in classes}


def split(rows):
    ids = sorted({r["image_id"] for r in rows})
    rng = np.random.default_rng(SEED)
    rng.shuffle(ids)
    n = len(ids)
    part = {i: ("train" if k < 0.6 * n else "val" if k < 0.8 * n else "test") for k, i in enumerate(ids)}
    return np.array([part[r["image_id"]] for r in rows])


def fit_temperature(logits, y):
    def nll(t):
        p = softmax(logits / t, axis=1)
        return -np.log(p[np.arange(len(y)), y] + 1e-12).mean()
    return float(minimize_scalar(nll, bounds=(0.05, 20), method="bounded").x)


def zero_shot_logits(X, classes):
    model, _, _ = open_clip.create_model_and_transforms("ViT-B-32", pretrained="openai")
    tok = open_clip.get_tokenizer("ViT-B-32")
    with torch.no_grad():
        t = model.encode_text(tok([f"a photo of {ITEMS[c].lower()}, litter" for c in classes]))
        t = (t / t.norm(dim=-1, keepdim=True)).numpy()
    return 100.0 * X @ t.T


def verdict_masses(P, classes, city):
    v = np.array([city.rules[c].verdict for c in classes])
    return {k: P[:, v == k].sum(1) for k in ("accept", "reject", "conditional")}, v


def run_methods(P, classes, city):
    """Return per-example (answer in {accept,reject,None}, confidence) for methods A and B."""
    m, v = verdict_masses(P, classes, city)
    top = P.argmax(1)
    a_ans = np.where(v[top] == "conditional", None, v[top])
    a_conf = np.where(v[top] == "conditional", 0.0, P.max(1))
    b_ans = np.where(m["accept"] >= m["reject"], "accept", "reject")
    b_conf = np.maximum(m["accept"], m["reject"])
    return {"A_item_confidence": (a_ans, a_conf), "B_verdict_mass": (b_ans, b_conf)}


def metrics(ans, conf, truth, t):
    answered = (conf >= t) & (ans != None)
    nonacc = truth != "accept"
    fa = answered & (ans == "accept") & nonacc
    missed = answered & (ans == "reject") & (truth == "accept")
    return answered.mean(), fa.sum() / max(nonacc.sum(), 1), missed.sum() / max((truth == "accept").sum(), 1)


def at_coverage(ans, conf, truth, target):
    best = None
    for t in np.unique(np.round(conf, 6)):
        cov, far, miss = metrics(ans, conf, truth, t)
        if cov >= target and (best is None or t > best[0]):
            best = (t, cov, far, miss)
    return best


def main():
    rows, X, classes, dropped = load()
    part = split(rows)
    y = np.array([classes.index(r["item"]) for r in rows])
    imgs = np.array([r["image_id"] for r in rows])
    tr, va, te = (part == "train"), (part == "val"), (part == "test")
    clf = LogisticRegression(C=10, max_iter=3000).fit(X[tr], y[tr])
    lg = clf.decision_function(X)
    T = fit_temperature(lg[va], y[va])
    probs = {"linear_probe": softmax(lg / T, axis=1)}
    probs["zero_shot"] = softmax(zero_shot_logits(X, classes), axis=1)
    out = {"classes": classes, "dropped_too_few_crops": dropped, "n_crops": len(rows),
           "split_crops": {k: int(s.sum()) for k, s in zip(("train", "val", "test"), (tr, va, te))},
           "temperature": T, "item_accuracy_test": {k: float((p[te].argmax(1) == y[te]).mean()) for k, p in probs.items()},
           "results": {}}
    rng = np.random.default_rng(1)
    test_imgs = np.unique(imgs[te])
    for model_name, P in probs.items():
        for cid in CITIES:
            city = load_city(cid)
            truth_all = np.array([city.rules[classes[k]].verdict for k in y])
            meths = run_methods(P, classes, city)
            for mname, (ans, conf) in meths.items():
                res = {}
                for tg in TARGETS:
                    pt = at_coverage(ans[te], conf[te], truth_all[te], tg)
                    if pt is None:
                        res[str(tg)] = None
                        continue
                    t = pt[0]
                    boots = []
                    for _ in range(300):
                        pick = rng.choice(test_imgs, len(test_imgs))
                        idx = np.concatenate([np.where(te & (imgs == i))[0] for i in pick])
                        boots.append(metrics(ans[idx], conf[idx], truth_all[idx], t)[1])
                    res[str(tg)] = {"threshold": float(t), "coverage": float(pt[1]), "false_accept_rate": float(pt[2]),
                                    "far_ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
                                    "missed_recyclable_rate": float(pt[3])}
                out["results"][f"{model_name}/{cid}/{mname}"] = res
    (ROOT / "eval").mkdir(exist_ok=True)
    (ROOT / "eval/results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    plot(probs["linear_probe"], classes, y, te, imgs)
    print(json.dumps({k: out[k] for k in ("n_crops", "split_crops", "temperature", "item_accuracy_test", "dropped_too_few_crops")}, indent=1))
    for k, v in out["results"].items():
        print(k, {t: (None if r is None else (round(r["coverage"], 2), round(r["false_accept_rate"], 3), [round(c, 3) for c in r["far_ci95"]])) for t, r in v.items()})


def plot(P, classes, y, te, imgs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, len(CITIES), figsize=(9, 3.6), sharey=True)
    for ax, cid in zip(axes, CITIES):
        city = load_city(cid)
        truth = np.array([city.rules[classes[k]].verdict for k in y])
        for mname, (ans, conf) in run_methods(P, classes, city).items():
            pts = sorted({(metrics(ans[te], conf[te], truth[te], t)[0], metrics(ans[te], conf[te], truth[te], t)[1])
                          for t in np.unique(np.round(conf[te], 4))})
            ax.plot(*zip(*pts), label=mname.replace("_", " "))
        ax.set_title(cid.replace("_", " ").title())
        ax.set_xlabel("coverage (fraction answered)")
    axes[0].set_ylabel("false-accept rate")
    axes[0].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(ROOT / "eval/far_vs_coverage.png", dpi=160)


if __name__ == "__main__":
    main()
