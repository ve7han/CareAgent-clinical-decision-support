"""
Diagnostic Reasoning Agent
---------------------------
Uses the trained XGBoost model to generate a ranked differential
diagnosis, then computes SHAP feature attributions for the top prediction.
"""

import os
import numpy as np
import shap
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data.mimic_simulator import FEATURE_COLS, DIAGNOSES
from models.trainer import load_model, load_explainer, model_exists, train_and_save

FEATURE_LABELS = {
    "heart_rate":       "Heart Rate",
    "systolic_bp":      "Systolic BP",
    "diastolic_bp":     "Diastolic BP",
    "respiratory_rate": "Respiratory Rate",
    "spo2":             "SpO₂",
    "temperature":      "Temperature",
    "wbc":              "WBC",
    "lactate":          "Lactate",
    "creatinine":       "Creatinine",
    "troponin":         "Troponin",
    "crp":              "CRP",
    "sodium":           "Sodium",
    "potassium":        "Potassium",
    "glucose":          "Glucose",
    "haemoglobin":      "Haemoglobin",
    "platelets":        "Platelets",
    "alt":              "ALT",
    "bilirubin":        "Bilirubin",
    "age":              "Age",
    "recent_infection": "Recent Infection",
    "diabetes":         "Diabetes",
    "hypertension":     "Hypertension Hx",
    "ckd":              "CKD",
    "cad":              "CAD",
}


def _acuity_multiplier(diagnosis: str) -> float:
    HIGH   = {"Septic Shock", "Acute MI", "Stroke", "Pulmonary Embolism"}
    MEDIUM = {"Sepsis", "DKA", "Heart Failure"}
    if diagnosis in HIGH:   return 1.6
    if diagnosis in MEDIUM: return 1.3
    return 1.0


class DiagnosticReasoningAgent:
    def __init__(self):
        self._model = None
        self._explainer = None

    def _ensure_model(self):
        if self._model is None:
            if not model_exists():
                print("[DiagnosticAgent] Model not found — training now …")
                train_and_save()
            self._model     = load_model()
            self._explainer = load_explainer()

    def reason(self, intake: dict) -> dict:
        self._ensure_model()
        raw = intake["raw"]

        # Build feature vector
        x = np.array([[float(raw.get(f, 0)) for f in FEATURE_COLS]], dtype=np.float32)

        # Get class probabilities
        proba = self._model.predict_proba(x)[0]  # shape (n_classes,)

        # Build differential list
        differentials = []
        for i, dx in enumerate(DIAGNOSES):
            base_prob = float(proba[i])
            am = _acuity_multiplier(dx)
            ccs = round(min(base_prob * am, 1.0), 3)
            differentials.append({
                "diagnosis":  dx,
                "probability": round(base_prob, 3),
                "ccs":         ccs,
                "acuity_multiplier": am,
            })
        differentials.sort(key=lambda d: d["ccs"], reverse=True)

        # SHAP for top diagnosis
        top_class_idx = DIAGNOSES.index(differentials[0]["diagnosis"])
        shap_values = self._explainer.shap_values(x)

        # shap_values may be list (one per class) or 3D array
        if isinstance(shap_values, list):
            sv = shap_values[top_class_idx][0]
        else:
            sv = shap_values[0, :, top_class_idx]

        # Top 8 contributing features (by absolute magnitude)
        feature_contributions = []
        for i, feat in enumerate(FEATURE_COLS):
            feature_contributions.append({
                "feature":  feat,
                "label":    FEATURE_LABELS.get(feat, feat),
                "value":    round(float(x[0, i]), 3),
                "shap":     round(float(sv[i]), 4),
                "abs_shap": round(abs(float(sv[i])), 4),
            })
        feature_contributions.sort(key=lambda f: f["abs_shap"], reverse=True)
        top_features = feature_contributions[:8]

        # Positive (supporting) and negative (against) top factors
        supporting = [f for f in top_features if f["shap"] > 0][:4]
        against    = [f for f in top_features if f["shap"] < 0][:3]

        return {
            "differentials":   differentials[:5],
            "all_differentials": differentials,
            "top_features":    top_features,
            "supporting":      supporting,
            "against":         against,
            "shap_base_value": round(float(self._explainer.expected_value[top_class_idx])
                                     if hasattr(self._explainer.expected_value, "__iter__")
                                     else float(self._explainer.expected_value), 4),
            "model_confidence": differentials[0]["ccs"],
        }
