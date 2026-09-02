"""
Phase 4 — Federated Learning Client (Insurer Node)
Crop Insurance Fraud Detection
"""

import os
import json
import numpy as np
import pandas as pd
import flwr as fl
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, roc_auc_score, average_precision_score, precision_score, recall_score
from typing import Dict, Tuple, List, Any

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


class InsuranceFLClient(fl.client.NumPyClient):
    """
    Flower NumPyClient representing a single independent Insurer Node.
    Holds private claims data and performs local XGBoost training.
    """

    def __init__(self, insurer_id: int):
        self.insurer_id = insurer_id
        csv_path = f"data/nodes/insurer_{insurer_id}.csv"
        
        # Load local private dataset
        df = pd.read_csv(csv_path, low_memory=False)
        df['cause_of_loss_code'] = pd.to_numeric(df['cause_of_loss_code'], errors='coerce').fillna(0)
        
        X = df[FEATURE_COLS].fillna(0)
        y = df[TARGET_COL]

        # 80/20 local train/val split
        self.X_train, self.X_val, self.y_train, self.y_val = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y if y.sum() > 5 else None
        )
        self.num_train = len(self.X_train)
        self.num_val = len(self.X_val)

        # Calculate local class weight
        fraud_count = max(int(self.y_train.sum()), 1)
        normal_count = int((self.y_train == 0).sum())
        self.scale_pos_weight = float(normal_count / fraud_count)

        self.model: xgb.XGBClassifier = None

    def get_parameters(self, config: Dict[str, Any]) -> List[np.ndarray]:
        """
        Extract model parameters (serialized booster JSON bytes)
        to send back to the FL Server.
        """
        if self.model is None:
            return [np.array([], dtype=np.uint8)]
        
        raw_json = self.model.get_booster().save_raw(raw_format="json")
        byte_arr = np.frombuffer(raw_json, dtype=np.uint8)
        return [byte_arr]

    def set_parameters(self, parameters: List[np.ndarray]):
        """
        Load global model parameters received from the FL Server.
        """
        if len(parameters) > 0 and parameters[0].size > 0:
            byte_arr = parameters[0]
            raw_bytes = byte_arr.tobytes()
            self.model = xgb.XGBClassifier()
            booster = xgb.Booster()
            booster.load_model(bytearray(raw_bytes))
            self.model._Booster = booster

    def fit(self, parameters: List[np.ndarray], config: Dict[str, Any]) -> Tuple[List[np.ndarray], int, Dict[str, Any]]:
        """
        Local Training step:
        Receive global model -> Train on private local claims -> Return updated weights
        """
        self.set_parameters(parameters)
        local_trees = int(config.get("local_trees", 20))
        learning_rate = float(config.get("learning_rate", 0.05))

        if self.model is None or not hasattr(self.model, "_Booster"):
            # First round initialization
            self.model = xgb.XGBClassifier(
                n_estimators=local_trees,
                max_depth=6,
                learning_rate=learning_rate,
                scale_pos_weight=self.scale_pos_weight,
                eval_metric="aucpr",
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42 + self.insurer_id,
                n_jobs=2,
                verbosity=0,
            )
            self.model.fit(self.X_train, self.y_train)
        else:
            # Continual boosting round on existing trees
            curr_trees = getattr(self.model, "n_estimators", None) or 15
            self.model.n_estimators = curr_trees + local_trees
            self.model.fit(self.X_train, self.y_train, xgb_model=self.model.get_booster())

        updated_params = self.get_parameters(config={})
        return updated_params, self.num_train, {"insurer_id": self.insurer_id}

    def evaluate(self, parameters: List[np.ndarray], config: Dict[str, Any]) -> Tuple[float, int, Dict[str, Any]]:
        """
        Local Evaluation step on node's validation set.
        """
        self.set_parameters(parameters)
        if self.model is None:
            return 1.0, self.num_val, {"f1": 0.0, "pr_auc": 0.0}

        y_prob = self.model.predict_proba(self.X_val)[:, 1]
        y_pred = (y_prob >= 0.5).astype(int)

        f1 = float(f1_score(self.y_val, y_pred, zero_division=0))
        pr_auc = float(average_precision_score(self.y_val, y_prob)) if self.y_val.sum() > 0 else 0.0
        loss = float(1.0 - pr_auc)

        return loss, self.num_val, {"f1": f1, "pr_auc": pr_auc}
