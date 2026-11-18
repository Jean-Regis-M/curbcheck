"""Encode all TrashNet images (cardboard, glass, metal, paper, trash; plastic kept for completeness) with the PyTorch
OpenCLIP ViT-B/32 QuickGELU encoder and cache features + labels in data/cache/."""
import json
from pathlib import Path

import numpy as np
import open_clip
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/raw/trashnet/dataset-resized"


def main():
    files = [(c, f) for c in ("cardboard", "glass", "metal", "paper", "plastic", "trash") for f in sorted((BASE / c).glob("*.jpg"))]
    model, _, pre = open_clip.create_model_and_transforms("ViT-B-32-quickgelu", pretrained="openai")
    model.eval()
    feats = []
    with torch.no_grad():
        for i in range(0, len(files), 32):
            x = torch.stack([pre(Image.open(f).convert("RGB")) for _, f in files[i:i + 32]])
            f = model.encode_image(x)
            feats.append((f / f.norm(dim=-1, keepdim=True)).numpy())
            if i % 320 == 0:
                print(i, len(files), flush=True)
    np.save(ROOT / "data/cache/trashnet_clip_b32.npy", np.concatenate(feats))
    (ROOT / "data/cache/trashnet_labels.json").write_text(json.dumps([c for c, _ in files]), encoding="utf-8")
    print("done", len(files))


if __name__ == "__main__":
    main()
