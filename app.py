"""
CareAgent Flask Application
----------------------------
Serves the demo dashboard and exposes a JSON API for the agent pipeline.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, render_template, request, jsonify
from agents.orchestrator import OrchestratorAgent
from data.mimic_simulator import DEMO_PATIENTS, FEATURE_COLS, generate_patient, DIAGNOSES
import numpy as np

app = Flask(__name__, template_folder="templates", static_folder="static")
orchestrator = OrchestratorAgent()


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html", demo_patients=list(DEMO_PATIENTS.keys()))


@app.route("/api/analyse", methods=["POST"])
def analyse():
    data = request.get_json(force=True)
    patient = data.get("patient", {})
    use_llm = data.get("use_llm", False)   # LLM off by default (no key in demo)

    # Convert numeric strings
    for key in FEATURE_COLS:
        if key in patient:
            try:
                patient[key] = float(patient[key])
            except (ValueError, TypeError):
                pass

    result = orchestrator.run(patient, use_llm=use_llm)
    return jsonify(result)


@app.route("/api/demo/<name>", methods=["GET"])
def demo_patient(name):
    if name not in DEMO_PATIENTS:
        return jsonify({"error": "Demo patient not found"}), 404
    return jsonify(DEMO_PATIENTS[name])


@app.route("/api/random", methods=["GET"])
def random_patient():
    rng = np.random.default_rng()
    dx  = request.args.get("diagnosis")
    if dx and dx not in DIAGNOSES:
        return jsonify({"error": f"Unknown diagnosis: {dx}"}), 400
    p = generate_patient(diagnosis=dx or None, rng=rng)
    return jsonify(p)


@app.route("/api/diagnoses", methods=["GET"])
def list_diagnoses():
    return jsonify(DIAGNOSES)


@app.route("/api/status", methods=["GET"])
def status():
    from models.trainer import model_exists
    return jsonify({
        "status":       "ok",
        "model_ready":  model_exists(),
        "llm_enabled":  bool(os.getenv("ANTHROPIC_API_KEY")),
    })


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  CareAgent — Clinical Decision Support System")
    print("  Starting at http://localhost:5000")
    print("="*60 + "\n")
    app.run(debug=False, host="0.0.0.0", port=5000)
