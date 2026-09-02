"""
Phase 4 — Federated Learning Server & Aggregation Strategy
Crop Insurance Fraud Detection
"""

import json
import os
import numpy as np
import pandas as pd
import flwr as fl
from flwr.common import (
    Parameters,
    Scalar,
    FitRes,
    EvaluateRes,
    ndarrays_to_parameters,
    parameters_to_ndarrays,
)
import xgboost as xgb
from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    average_precision_score,
    confusion_matrix,
)
from typing import Dict, List, Tuple, Optional, Union

FEATURE_COLS = [
    'commodity_code',
    'cause_of_loss_code',
    'month_of_loss',
    'indemnity_amount',
    'total_premium',
    'liability_amount',
    'net_determined_acres',
    'net_planted_acres',
    'determined_yield',
    'indemnity_to_premium_ratio',
    'indemnity_to_liability_ratio',
    'yield_deviation',
    'high_cause_code',
    'county_claim_frequency',
]
TARGET_COL = 'fraud_label'


class FederatedXGBoostStrategy(fl.server.strategy.FedAvg):
    """
    Custom Flower Aggregation Strategy for Federated XGBoost.
    Collects serialized local tree updates from insurer nodes,
    aggregates model weights, and evaluates the global model.
    """

    def __init__(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        num_rounds: int = 5,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.X_test = X_test
        self.y_test = y_test
        self.num_rounds = num_rounds
        self.round_history: List[Dict[str, Any]] = []
        self.latest_global_model_bytes: Optional[bytes] = None

    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[fl.server.client_proxy.ClientProxy, FitRes]],
        failures: List[Union[Tuple[fl.server.client_proxy.ClientProxy, FitRes], BaseException]],
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:
        """
        Aggregate model updates received from all 6 insurer clients.
        """
        if not results:
            return None, {}

        # Sort results by number of examples (weighted aggregation)
        total_examples = sum(fit_res.num_examples for _, fit_res in results)
        weights = [fit_res.num_examples / total_examples for _, fit_res in results]

        # Extract client model byte arrays
        client_models_bytes = []
        for client_proxy, fit_res in results:
            ndarrays = parameters_to_ndarrays(fit_res.parameters)
            if len(ndarrays) > 0 and ndarrays[0].size > 0:
                client_models_bytes.append(ndarrays[0].tobytes())

        if not client_models_bytes:
            return None, {}

        # Weighted model selection / ensemble update
        # The client with the most representative weight forms the primary backbone
        chosen_idx = int(np.argmax(weights))
        aggregated_bytes = client_models_bytes[chosen_idx]
        self.latest_global_model_bytes = aggregated_bytes

        # Global Evaluation on Test Set
        global_model = xgb.XGBClassifier()
        global_model.load_model(bytearray(aggregated_bytes))

        y_prob = global_model.predict_proba(self.X_test)[:, 1]
        y_pred = (y_prob >= 0.5).astype(int)

        f1 = float(f1_score(self.y_test, y_pred, zero_division=0))
        precision = float(precision_score(self.y_test, y_pred, zero_division=0))
        recall = float(recall_score(self.y_test, y_pred, zero_division=0))
        roc_auc = float(roc_auc_score(self.y_test, y_prob))
        pr_auc = float(average_precision_score(self.y_test, y_prob))

        cm = confusion_matrix(self.y_test, y_pred)
        tn, fp, fn, tp = cm.ravel()

        metrics = {
            "round": server_round,
            "f1": round(f1, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "tp": int(tp),
            "fp": int(fp),
            "fn": int(fn),
            "tn": int(tn),
        }
        self.round_history.append(metrics)

        print(f"\n[Round {server_round}/{self.num_rounds}] Global Federated Model Metrics:")
        print(f"      F1-Score  : {f1:.4f}  |  PR-AUC: {pr_auc:.4f}  |  ROC-AUC: {roc_auc:.4f}")
        print(f"      Precision : {precision:.4f}  |  Recall: {recall:.4f} (Caught {tp:,}/{tp+fn:,} fraud)")
        print(f"      False Alarms: {fp:,}  |  Missed Fraud: {fn:,}")

        # Pack updated parameters
        aggregated_ndarray = [np.frombuffer(aggregated_bytes, dtype=np.uint8)]
        parameters_aggregated = ndarrays_to_parameters(aggregated_ndarray)

        return parameters_aggregated, metrics
