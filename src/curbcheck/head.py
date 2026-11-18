"""Item probabilities from cached image features and a saved head (models/*.npz), including the optional zero-shot blend."""
from __future__ import annotations

import numpy as np
from scipy.special import softmax


def probs_from_features(X: np.ndarray, head) -> np.ndarray:
    z = X @ head["W"].T + head["b"]
    if "zs_text" in head.files:
        z = z + float(head["zs_scale"]) * (X @ head["zs_text"].T)
    return softmax(z / float(head["T"]), axis=1)
