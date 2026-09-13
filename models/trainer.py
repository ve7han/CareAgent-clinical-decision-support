"""
Model Trainer
-------------
Trains an XGBoost multi-class classifier on synthetic MIMIC-III data.
Saves the model and a background SHAP explainer to disk.
"""

import os
import pickle
import numpy as np
import pandas as pd
import xgboost as xgb
import shap
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data.mimic_simulator import generate_dataset, FEATURE_COLS, DIAGNOSES

MODEL_PATH  = os.path.join(os.path.dirname(__file__), "careagent_model.pkl")
SHAP_PATH   = os.path.join(os.path.dirname(__file__), "shap_explainer.pkl")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "eval_report.txt")


def train_and_save(n_samples: int = 3000, seed: int = 42) -> dict:
    print("Generating synthetic MIMIC-III data …")
    df = generate_dataset(n=n_samples, seed=seed)

    X = df[FEATURE_COLS].values.astype(np.float32)
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )

    print(f"Training XGBoost on {len(X_train)} samples ({len(DIAGNOSES)} classes) …")
    model = xgb.XGBClassifier(
        n_estimators=350,
        max_depth=6,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.80,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=seed,
        verbosity=0,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=DIAGNOSES)

    print(f"\nTest accuracy: {acc:.3f}\n")
    print(report)

    with open(REPORT_PATH, "w") as f:
        f.write(f"Test accuracy: {acc:.4f}\n\n{report}")

    print("Building SHAP TreeExplainer (background = 200 samples) …")
    bg_idx = np.random.default_rng(seed).choice(len(X_train), size=200, replace=False)
    explainer = shap.TreeExplainer(model, data=X_train[bg_idx])

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(SHAP_PATH, "wb") as f:
        pickle.dump(explainer, f)

    print(f"Model saved  → {MODEL_PATH}")
    print(f"Explainer saved → {SHAP_PATH}")
    return {"accuracy": acc, "report": report}


def load_model():
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)

def load_explainer():
    with open(SHAP_PATH, "rb") as f:
        return pickle.load(f)

def model_exists() -> bool:
    return os.path.exists(MODEL_PATH) and os.path.exists(SHAP_PATH)


if __name__ == "__main__":
    train_and_save()
