# CareAgent — AI Clinical Decision Support System
## Multi-Agent Prototype · BSc Artificial Intelligence · Northumbria University

---

## What This Is

CareAgent is a working multi-agent AI prototype that automates clinical
decision support for acute care patients.  It uses:

- **XGBoost + SHAP** for diagnosis and feature attribution
- **5 collaborating Python agents** (Orchestrator, Intake, Diagnostic, Treatment, Liaison)
- **Synthetic MIMIC-III data** (clinically realistic ICU distributions)
- **NICE/WHO/Surviving Sepsis Campaign** knowledge base (10 diagnoses)
- **Flask + vanilla JS** dashboard interface

---

## Quick Start

### 1. Install dependencies

```bash
cd careagent
pip install -r requirements.txt
```

### 2. Train the model (first run only — takes ~30 seconds)

```bash
python models/trainer.py
```

This generates:
- `models/careagent_model.pkl`  — XGBoost classifier (93% test accuracy)
- `models/shap_explainer.pkl`   — TreeExplainer for SHAP values
- `models/eval_report.txt`      — Per-class classification report

### 3. Run the app

```bash
python app.py
```

Open: **http://localhost:5000**

---

## Optional: Claude API for richer narratives

Set your API key and the Clinician Liaison Agent will use Claude to generate
richer plain-language clinical summaries:

```bash
export ANTHROPIC_API_KEY=your_key_here
python app.py
```

---

## Project Structure

```
careagent/
├── app.py                        # Flask web app + REST API
├── requirements.txt
├── agents/
│   ├── orchestrator.py           # Coordinates all sub-agents
│   ├── intake_agent.py           # Clinical flag detection + vitals parsing
│   ├── diagnostic_agent.py       # XGBoost + SHAP differential diagnosis
│   ├── treatment_agent.py        # NICE/WHO guideline knowledge base
│   └── liaison_agent.py          # Plain-language report + counterfactuals
├── data/
│   └── mimic_simulator.py        # Synthetic MIMIC-III patient generator
├── models/
│   ├── trainer.py                # XGBoost training script
│   ├── careagent_model.pkl       # Trained model (after training)
│   └── shap_explainer.pkl        # SHAP explainer (after training)
└── templates/
    └── index.html                # Full dashboard UI
```

---

## Agent Pipeline

```
Patient Data (JSON)
      │
      ▼
┌─────────────────────┐
│  Orchestrator Agent │  ← coordinates all agents
└─────────────────────┘
      │
      ├──▶ Patient Intake Agent
      │    • Parses 24 clinical features
      │    • Computes 30+ clinical flags
      │    • Calculates qSOFA score
      │
      ├──▶ Diagnostic Reasoning Agent
      │    • XGBoost → 10-class differential
      │    • SHAP feature attribution
      │    • Contextual Clinical Score (CCS)
      │
      ├──▶ Treatment Planner Agent
      │    • NICE/WHO guideline matching
      │    • Patient-specific personalisation
      │    • Time-critical bundle windows
      │
      └──▶ Clinician Liaison Agent
           • Plain-language narrative
           • Counterfactual explanation
           • Trust score calibration
           • Optional Claude API enrichment
```

---

## Supported Diagnoses

1. Sepsis
2. Septic Shock
3. Acute MI
4. Heart Failure
5. Pneumonia
6. AKI
7. Pulmonary Embolism
8. Stroke
9. DKA
10. COPD Exacerbation

---

## API Endpoints

| Method | Endpoint              | Description                        |
|--------|-----------------------|------------------------------------|
| POST   | /api/analyse          | Run full pipeline on patient data  |
| GET    | /api/demo/<name>      | Load a preset demo patient         |
| GET    | /api/random           | Generate random synthetic patient  |
| GET    | /api/diagnoses        | List all supported diagnoses       |
| GET    | /api/status           | System status + model ready check  |

---

## Demo Patients

| Name            | Profile                                        |
|-----------------|------------------------------------------------|
| sepsis_classic  | 67yr M · Fever, Hypotension, Lactate 3.8       |
| ami_stemi       | 58yr M · Troponin 4.8, CAD, Diabetes           |
| dka_young       | 24yr F · Glucose 32.5, Potassium 5.8, T1DM    |

---

## ⚠ Disclaimer

This is an academic research prototype.  All outputs are AI-generated and
have NOT been validated for clinical use.  Do not use to make real clinical
decisions.  Every clinical decision must be made by a qualified clinician
who takes full professional responsibility.
