"""
Phase 5 — Differential Privacy & Secure Aggregation Mechanisms for Tree Models
Crop Insurance Fraud Detection

Implements:
  1. Tree Leaf Weight Sensitivity Bounding (L2 Norm Clipping)
  2. Tree Weight Gaussian Perturbation (Local Differential Privacy)
  3. Zero-Sum Pairwise Masking (SecAgg Simulation)
"""

import os
import json
import numpy as np
import secrets
from typing import List, Tuple, Dict, Any


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


class PairwiseSecureAggregator:
    """
    Simulates Pairwise Masking Secure Aggregation (SecAgg).
    
    Between every pair of clients (i, j) with i < j:
      - Client i adds  + R_{i, j}
      - Client j adds  - R_{i, j}
    When server computes Sum(Masked_i) across all N clients:
      Sum(R_{i,j} - R_{i,j}) = 0 (perfect zero-sum cancellation!)
    """

    @staticmethod
    def generate_pairwise_masks(num_clients: int, array_length: int, base_seed: int = 42) -> List[np.ndarray]:
        """
        Generate zero-sum pairwise cryptographic random masks for all clients.
        """
        client_masks = [np.zeros(array_length, dtype=np.float64) for _ in range(num_clients)]

        pair_id = 0
        for i in range(num_clients):
            for j in range(i + 1, num_clients):
                pair_seed = (base_seed * 1000 + pair_id) % (2**31 - 1)
                rng = np.random.RandomState(pair_seed)
                mask_ij = rng.normal(loc=0.0, scale=1.0, size=array_length)

                client_masks[i] += mask_ij
                client_masks[j] -= mask_ij
                pair_id += 1

        # Verify zero-sum property
        mask_sum = np.sum(client_masks, axis=0)
        assert np.allclose(mask_sum, 0.0, atol=1e-8), "SecAgg mask sum does not cancel to 0!"

        return client_masks

    @staticmethod
    def mask_parameters(param_array: np.ndarray, client_mask: np.ndarray) -> np.ndarray:
        """Apply zero-sum cryptographic mask to client update array."""
        target_len = len(client_mask)
        if len(param_array) < target_len:
            padded = np.zeros(target_len, dtype=np.float64)
            padded[:len(param_array)] = param_array
            param_array = padded
        elif len(param_array) > target_len:
            param_array = param_array[:target_len]
        return param_array.astype(np.float64) + client_mask

    @staticmethod
    def aggregate_masked_updates(masked_arrays: List[np.ndarray]) -> np.ndarray:
        """
        Server-side aggregation:
        Summing all masked arrays cancels all masks to 0 automatically.
        """
        return np.sum(masked_arrays, axis=0) / len(masked_arrays)
