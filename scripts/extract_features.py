"""Encode crops with OpenCLIP ViT-B/32 (OpenAI weights) on CPU and cache to data/cache/."""
import json
from pathlib import Path

import numpy as np
import open_clip
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CROPS = ROOT / "data" / "raw" / "taco" / "crops"


def main():
    rows = json.loads((ROOT / "data/raw/taco/crops.json").read_text("utf-8"))
    model, _, pre = open_clip.create_model_and_transforms("ViT-B-32", pretrained="openai")
    model.eval()
    feats = []
    with torch.no_grad():
        for i in range(0, len(rows), 32):
            batch = torch.stack([pre(Image.open(CROPS / r["crop"]).convert("RGB")) for r in rows[i:i + 32]])
            f = model.encode_image(batch)
            feats.append((f / f.norm(dim=-1, keepdim=True)).numpy())
            print(i, end=" ", flush=True)
    (ROOT / "data/cache").mkdir(exist_ok=True)
    np.save(ROOT / "data/cache/taco_clip_b32.npy", np.concatenate(feats))
    print("\nsaved", len(rows))


if __name__ == "__main__":
    main()
