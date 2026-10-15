"""
Phase 5 — Differential Privacy Mechanisms for Tree Models
Crop Insurance Fraud Detection

Implements:
  1. Tree Leaf Weight Sensitivity Bounding (L2 Norm Clipping)
  2. Tree Weight Gaussian Perturbation (Local Differential Privacy)
"""

import json
import numpy as np
import secrets
from typing import Tuple, Dict


def apply_tree_differential_privacy(
    raw_json_bytes: bytes,
    clip_norm: float = 1.0,
    noise_multiplier: float = 0.02,
    seed: int = None
) -> Tuple[bytes, Dict[str, float]]:
    """
    Applies Local Differential Privacy directly to the XGBoost Tree Leaf Weights:
      1. Parses JSON model representation
      2. Extracts all leaf prediction logits ('base_weights')
      3. Performs L2 norm clipping (||W|| <= C)
      4. Injects calibrated Gaussian noise N(0, (sigma * C)^2)
      5. Re-assembles mathematically perturbed trees into valid JSON
    """
    if noise_multiplier <= 0.0 and clip_norm <= 0.0:
        return raw_json_bytes, {"clip_norm": 0.0, "noise_multiplier": 0.0, "l2_norm_before": 0.0}

    try:
        model_dict = json.loads(raw_json_bytes.decode('utf-8'))
    except Exception:
        return raw_json_bytes, {}

    trees = model_dict.get('learner', {}).get('gradient_booster', {}).get('model', {}).get('trees', [])
    if not trees:
        return raw_json_bytes, {}

    # Extract all leaf weights into flat vector
    all_weights = []
    tree_slices = []
    curr_idx = 0

    for t in trees:
        w_list = t.get('base_weights', [])
        length = len(w_list)
        all_weights.extend(w_list)
        tree_slices.append((curr_idx, curr_idx + length))
        curr_idx += length

    if not all_weights:
        return raw_json_bytes, {}

    w_arr = np.array(all_weights, dtype=np.float64)
    l2_norm_before = float(np.linalg.norm(w_arr))

    # 1. L2 Norm Clipping
    if clip_norm > 0 and l2_norm_before > clip_norm:
        scaling = clip_norm / l2_norm_before
        w_arr = w_arr * scaling

    # 2. Gaussian Noise Injection
    if noise_multiplier > 0:
        if seed is not None:
            rng = np.random.RandomState(seed % (2**31 - 1))
        else:
            rng = np.random.RandomState(int.from_bytes(secrets.token_bytes(4), "big"))
        
        sigma = noise_multiplier * (clip_norm if clip_norm > 0 else 1.0)
        noise = rng.normal(loc=0.0, scale=sigma, size=w_arr.shape)
        w_arr = w_arr + noise

    # 3. Re-inject perturbed weights back into tree structures
    for idx, (start, end) in enumerate(tree_slices):
        trees[idx]['base_weights'] = [round(float(val), 7) for val in w_arr[start:end]]

    perturbed_json_bytes = json.dumps(model_dict).encode('utf-8')
    stats = {
        "clip_norm": clip_norm,
        "noise_multiplier": noise_multiplier,
        "l2_norm_before": round(l2_norm_before, 4),
        "total_leaf_weights": len(all_weights),
    }
    return perturbed_json_bytes, stats

