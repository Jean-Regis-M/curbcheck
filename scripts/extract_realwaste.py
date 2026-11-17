"""Encode all RealWaste images (parquet shards in data/raw/realwaste/) with CLIP ViT-B/32 and cache features + labels."""
import io
import json
import re
from pathlib import Path

import numpy as np
import open_clip
import pyarrow.parquet as pq
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    recs = []
    for shard in sorted((ROOT / "data/raw/realwaste").glob("p*.parquet")):
        recs += pq.read_table(shard, columns=["image"]).column("image").to_pylist()
    labels = [re.sub(r"_\d+\.\w+$", "", r["path"]) for r in recs]
    model, _, pre = open_clip.create_model_and_transforms("ViT-B-32-quickgelu", pretrained="openai")
    model.eval()
    feats = []
    with torch.no_grad():
        for i in range(0, len(recs), 32):
            x = torch.stack([pre(Image.open(io.BytesIO(r["bytes"])).convert("RGB")) for r in recs[i:i + 32]])
            f = model.encode_image(x)
            feats.append((f / f.norm(dim=-1, keepdim=True)).numpy())
            if i % 640 == 0:
                print(i, len(recs), flush=True)
    np.save(ROOT / "data/cache/realwaste_clip_b32.npy", np.concatenate(feats))
    (ROOT / "data/cache/realwaste_labels.json").write_text(json.dumps(labels), encoding="utf-8")
    print("done", len(recs))


if __name__ == "__main__":
    main()
