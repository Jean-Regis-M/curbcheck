"""Image -> item probabilities. CLIP ViT-B/32 (CPU) encoder + the trained linear head in models/head.npz."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

import numpy as np
from PIL import Image
from scipy.special import softmax

HEAD = Path(__file__).resolve().parents[2] / "models" / "head.npz"


class Classifier(Protocol):
    classes: list[str]
    threshold: float

    def predict(self, image: Image.Image) -> dict[str, float]: ...


class ClipHeadClassifier:
    def __init__(self, head_path: Path = HEAD):
        import open_clip
        import torch

        h = np.load(head_path, allow_pickle=False)
        self.W, self.b, self.T = h["W"], h["b"], float(h["T"])
        # optional zero-shot blend: CLIP text embeddings of the item prompts, weighted by zs_scale
        self.zs_text = h["zs_text"] if "zs_text" in h.files else None
        self.zs_scale = float(h["zs_scale"]) if "zs_scale" in h.files else 0.0
        self.classes = [str(c) for c in h["classes"]]
        self.threshold = float(h["threshold"])
        self._torch = torch
        self._model, _, self._pre = open_clip.create_model_and_transforms("ViT-B-32-quickgelu", pretrained="openai")
        self._model.eval()

    def predict(self, image: Image.Image) -> dict[str, float]:
        with self._torch.no_grad():
            f = self._model.encode_image(self._pre(image.convert("RGB")).unsqueeze(0))
            f = (f / f.norm(dim=-1, keepdim=True)).numpy()[0]
        z = self.W @ f + self.b
        if self.zs_text is not None:
            z = z + self.zs_scale * (self.zs_text @ f)
        p = softmax(z / self.T)
        return {c: float(v) for c, v in zip(self.classes, p)}
