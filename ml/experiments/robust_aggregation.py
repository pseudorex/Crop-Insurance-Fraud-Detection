"""
Phase 6 — Robust Aggregation Defenses & Anomaly Detection Engine
Federated Crop Insurance Fraud Detection

Provides Byzantine-tolerant aggregation mechanisms and anomaly detection
to protect Federated Learning against poisoning attacks:
  1. Norm-Based Outlier Rejection (Adaptive L2 thresholding)
  2. Coordinate-Wise Trimmed Mean Aggregation
  3. Coordinate-Wise Median Aggregation
  4. Multi-Krum Geometric Consensus Selection
  5. Cryptographic Anomaly Audit Logger (SHA-256 commitments for Fabric)
"""

import os
import json
import hashlib
import time
import numpy as np
from typing import List, Tuple, Dict, Any, Optional


def extract_tree_weights(raw_json_bytes: bytes) -> Tuple[np.ndarray, List[Tuple[int, int]], Dict[str, Any]]:
    """
    Extracts leaf weights ('base_weights') from serialized XGBoost JSON model bytes.
    Returns:
      - w_arr: 1D numpy array of all concatenated leaf weights
      - tree_slices: list of (start, end) index tuples for each tree
      - model_dict: full parsed JSON dictionary
    """
    try:
        model_dict = json.loads(raw_json_bytes.decode('utf-8'))
    except Exception as e:
        return np.array([]), [], {}

    trees = model_dict.get('learner', {}).get('gradient_booster', {}).get('model', {}).get('trees', [])
    if not trees:
        return np.array([]), [], model_dict

    all_weights = []
    tree_slices = []
    curr_idx = 0

    for t in trees:
        w_list = t.get('base_weights', [])
        length = len(w_list)
        all_weights.extend(w_list)
        tree_slices.append((curr_idx, curr_idx + length))
        curr_idx += length

    w_arr = np.array(all_weights, dtype=np.float64)
    return w_arr, tree_slices, model_dict


def reassemble_tree_weights(model_dict: Dict[str, Any], tree_slices: List[Tuple[int, int]], w_arr: np.ndarray) -> bytes:
    """
    Re-injects updated/aggregated leaf weights back into the XGBoost tree structure
    and serializes back to JSON bytes.
    """
    trees = model_dict.get('learner', {}).get('gradient_booster', {}).get('model', {}).get('trees', [])
    for idx, (start, end) in enumerate(tree_slices):
        trees[idx]['base_weights'] = [round(float(val), 7) for val in w_arr[start:end]]

    return json.dumps(model_dict).encode('utf-8')


# ── Defense 1: Adaptive Norm-Based Outlier Rejection ───────────────────────────

def norm_outlier_rejection(
    updates: List[Tuple[bytes, int, int]],
    multiplier: float = 2.0,
    round_num: int = 1,
) -> Tuple[List[Tuple[bytes, int, int]], List[Dict[str, Any]]]:
    """
    Computes the L2 norm of each insurer's model update.
    Rejects any update whose L2 norm exceeds multiplier * median(L2 norms).
    
    Args:
        updates: List of (raw_bytes, num_samples, insurer_id)
        multiplier: Outlier threshold multiplier relative to median norm (default 2.0)
        round_num: Current FL training round
    
    Returns:
        good_updates: Filtered list of honest/admitted updates
        anomalies: List of anomaly audit logs for rejected updates
    """
    if len(updates) <= 2:
        return updates, []

    norms = []
    parsed_data = []

    for raw_bytes, num_samples, insurer_id in updates:
        w_arr, slices, m_dict = extract_tree_weights(raw_bytes)
        norm_val = float(np.linalg.norm(w_arr)) if len(w_arr) > 0 else 0.0
        norms.append(norm_val)
        parsed_data.append((raw_bytes, num_samples, insurer_id, norm_val, w_arr))

    norms = np.array(norms)
    median_norm = float(np.median(norms))
    threshold = max(multiplier * median_norm, 2.5)

    good_updates = []
    anomalies = []

    for raw_bytes, num_samples, insurer_id, norm_val, w_arr in parsed_data:
        if norm_val <= threshold:
            good_updates.append((raw_bytes, num_samples, insurer_id))
        else:
            # Generate cryptographic SHA-256 hash of the rogue payload
            update_hash = hashlib.sha256(raw_bytes).hexdigest()
            anomaly_record = {
                "round": round_num,
                "insurer_id": insurer_id,
                "anonymized_node_ref": hashlib.sha256(f"INSURER_{insurer_id}_SALT".encode()).hexdigest()[:16],
                "reason_code": "EXCESSIVE_L2_NORM_OUTLIER",
                "observed_norm": round(norm_val, 4),
                "threshold_norm": round(threshold, 4),
                "median_norm": round(median_norm, 4),
                "update_sha256": update_hash,
                "timestamp": int(time.time()),
                "action": "QUARANTINED_AND_REJECTED"
            }
            anomalies.append(anomaly_record)

    # Fallback: if all updates were somehow rejected, return original
    if not good_updates:
        good_updates = updates

    return good_updates, anomalies


# ── Defense 2: Coordinate-Wise Trimmed Mean Aggregation ───────────────────────

def trimmed_mean_aggregation(
    updates: List[Tuple[bytes, int, int]],
    trim_fraction: float = 0.15
) -> bytes:
    """
    Performs coordinate-wise trimmed mean across client tree leaf weights:
    Sorts values per coordinate/leaf, trims top and bottom k elements, and takes mean.
    
    Args:
        updates: List of (raw_bytes, num_samples, insurer_id)
        trim_fraction: Fraction of extreme values to trim on each side (default 0.15)
    """
    if not updates:
        return b""
    if len(updates) == 1:
        return updates[0][0]

    extracted = [extract_tree_weights(u[0]) for u in updates]
    weights_list = [w for w, _, _ in extracted if len(w) > 0]
    
    if not weights_list:
        return updates[0][0]

    # Best client template based on sample count
    best_client_idx = int(np.argmax([u[1] for u in updates]))
    ref_weights, ref_slices, ref_dict = extracted[best_client_idx]
    target_len = len(ref_weights)

    # Pad/truncate all weight vectors to target_len
    aligned_weights = []
    for w in weights_list:
        if len(w) == target_len:
            aligned_weights.append(w)
        elif len(w) < target_len:
            padded = np.pad(w, (0, target_len - len(w)), mode='constant')
            aligned_weights.append(padded)
        else:
            aligned_weights.append(w[:target_len])

    stacked = np.stack(aligned_weights, axis=0)  # Shape: (N_clients, target_len)
    n = stacked.shape[0]
    k = max(1, int(n * trim_fraction)) if n >= 4 else 0

    if k > 0 and (n - 2 * k) > 0:
        sorted_vals = np.sort(stacked, axis=0)
        trimmed = sorted_vals[k: n - k, :]
        aggregated_weights = np.mean(trimmed, axis=0)
    else:
        aggregated_weights = np.mean(stacked, axis=0)

    return reassemble_tree_weights(ref_dict, ref_slices, aggregated_weights)


# ── Defense 3: Coordinate-Wise Median Aggregation ─────────────────────────────

def median_aggregation(updates: List[Tuple[bytes, int, int]]) -> bytes:
    """
    Performs coordinate-wise median across client tree leaf weights.
    Provides robust Byzantine tolerance against arbitrary unbounded leaf updates.
    """
    if not updates:
        return b""
    if len(updates) == 1:
        return updates[0][0]

    extracted = [extract_tree_weights(u[0]) for u in updates]
    weights_list = [w for w, _, _ in extracted if len(w) > 0]

    if not weights_list:
        return updates[0][0]

    best_client_idx = int(np.argmax([u[1] for u in updates]))
    ref_weights, ref_slices, ref_dict = extracted[best_client_idx]
    target_len = len(ref_weights)

    aligned_weights = []
    for w in weights_list:
        if len(w) == target_len:
            aligned_weights.append(w)
        elif len(w) < target_len:
            padded = np.pad(w, (0, target_len - len(w)), mode='constant')
            aligned_weights.append(padded)
        else:
            aligned_weights.append(w[:target_len])

    stacked = np.stack(aligned_weights, axis=0)
    aggregated_weights = np.median(stacked, axis=0)

    return reassemble_tree_weights(ref_dict, ref_slices, aggregated_weights)


# ── Defense 4: Multi-Krum Geometric Consensus Selection ───────────────────────

def multi_krum_selection(
    updates: List[Tuple[bytes, int, int]],
    num_to_select: int = 4,
    num_byzantine: int = 1
) -> Tuple[List[Tuple[bytes, int, int]], List[int]]:
    """
    Multi-Krum defense: computes pairwise Euclidean distances between all updates
    and selects the clients that minimize cumulative distance to closest neighbors.
    
    Args:
        updates: List of (raw_bytes, num_samples, insurer_id)
        num_to_select: Number of benign updates to keep
        num_byzantine: Assumed upper bound on malicious clients
    
    Returns:
        selected_updates: Updates selected by Multi-Krum
        rejected_indices: Indices of rejected clients
    """
    n = len(updates)
    if n <= 2:
        return updates, []

    extracted = [extract_tree_weights(u[0]) for u in updates]
    weights_list = [w for w, _, _ in extracted]

    # Align lengths to max_len for accurate Euclidean distance calculation
    max_len = max(len(w) for w in weights_list) if weights_list else 0
    padded_weights = []
    for w in weights_list:
        if len(w) < max_len:
            padded_weights.append(np.pad(w, (0, max_len - len(w)), mode='constant'))
        else:
            padded_weights.append(w)

    # Pairwise distance matrix
    dist_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            d = float(np.linalg.norm(padded_weights[i] - padded_weights[j]) ** 2)
            dist_matrix[i, j] = d
            dist_matrix[j, i] = d

    # For each client i, sum the (n - f - 2) smallest distances (excluding self)
    k = max(1, n - num_byzantine - 2)
    scores = []
    for i in range(n):
        row = np.delete(dist_matrix[i], i)
        sorted_dists = np.sort(row)
        score = float(np.sum(sorted_dists[:k]))
        scores.append(score)

    sorted_indices = np.argsort(scores)
    selected_indices = sorted_indices[:min(num_to_select, n)]
    rejected_indices = sorted_indices[min(num_to_select, n):]

    selected_updates = [updates[idx] for idx in selected_indices]
    return selected_updates, list(rejected_indices)


# ── Cryptographic Anomaly Audit Logger ────────────────────────────────────────

class AnomalyAuditLogger:
    """
    Maintains an audit ledger of all detected malicious and anomalous events.
    Outputs structured tamper-evident records formatted for Hyperledger Fabric chaincode.
    """

    def __init__(self, log_path: str = "evaluation/anomaly_audit_log.json"):
        self.log_path = log_path
        self.events: List[Dict[str, Any]] = []

    def log_anomaly(self, anomaly_event: Dict[str, Any]):
        """Append an anomaly event."""
        self.events.append(anomaly_event)

    def save_ledger(self):
        """Persist all anomaly logs to JSON file."""
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        with open(self.log_path, 'w') as f:
            json.dump({
                "audit_title": "Federated Learning Byzantine Anomaly Audit Ledger",
                "total_anomalies_flagged": len(self.events),
                "timestamp": int(time.time()),
                "records": self.events
            }, f, indent=2)
