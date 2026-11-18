"""Promote the chosen multi-domain configuration (from scripts/train_v3.py) to the shipped head, models/head.npz.
The shipped head adds the CLIP text embeddings (zero-shot blend) to the saved linear head.
Chosen operating point: zero-shot weight 2.0, no class re-weighting, validation coverage target 0.55 (see README).
Usage: python scripts/export_v3.py        (PyTorch head -> models/head.npz)
       python scripts/export_v3.py web    (browser head -> models/head_web.npz)
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ZS_WEIGHT = 2.0
ZS_SCALE = ZS_WEIGHT * 0.1 * 100  # train_v3.py adds lambda * 0.1 * (100 * cosine) to each logit, so the weight on cosine is 20
WEB = len(sys.argv) > 1 and sys.argv[1] == "web"
SUF = "_web" if WEB else ""
CAND = ROOT / f"models/cand_v3{SUF}_zs2.0_None_cov0.55.npz"
OUT = ROOT / ("models/head_web.npz" if WEB else "models/head.npz")


def main():
    h = np.load(CAND, allow_pickle=False)
    np.savez(OUT, W=h["W"], b=h["b"], T=h["T"], threshold=h["threshold"], classes=h["classes"],
             zs_text=np.load(ROOT / f"models/zs_text_v3{SUF}.npy"), zs_scale=ZS_SCALE)
    print("wrote", OUT.name, "classes:", len(h["classes"]), "threshold:", float(h["threshold"]))


if __name__ == "__main__":
    main()
