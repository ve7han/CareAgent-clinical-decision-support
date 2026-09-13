# CareAgent

**A multi-agent clinical decision support system with explainable AI.**

CareAgent takes a patient's vital signs and laboratory results, routes them through four specialist agents, and produces a ranked differential diagnosis, a guideline-based treatment plan, and a clinical summary with an explanation of *why* each decision was made.

Built as an MSc group project on the AI Technology programme at Northumbria University London.

> **Note on data:** CareAgent does not use real patient data. Training and demo patients are synthetic, generated to reproduce the statistical patterns of the MIMIC-III critical care database, which is access-restricted. See [Data](#data) below.

---

## Why explainability matters here

A model that outputs "Sepsis, 68% confidence" is not clinically useful. A clinician cannot act on a number without knowing what drove it, and cannot challenge it without knowing what would change it.

CareAgent attaches three things to every decision:

- **Attribution**  which specific measurements pushed the model toward this diagnosis, via SHAP
- **Counterfactuals**  what would have to be different for the answer to change, for example: if lactate had been normal, confidence in sepsis drops and pneumonia becomes the leading diagnosis
- **A trust score**  an indication of how much weight the output should be given

The goal is a system that supports a clinical decision rather than replacing one.

---

## Architecture

A patient record passes through four specialist agents, coordinated by an orchestrator:

```
Patient data
     │
     ▼
┌─────────────────┐
│  Orchestrator   │  times each step, isolates errors
└────────┬────────┘
         │
         ▼
   Intake Agent      → flags abnormal vitals, qSOFA score, comorbidities
         │
         ▼
   Diagnostic Agent  → XGBoost ranking + SHAP attribution
         │
         ▼
   Treatment Agent   → matches guidelines, adjusts for patient factors
         │
         ▼
   Liaison Agent     → clinical narrative + counterfactual + trust score
         │
         ▼
    Final report → dashboard
```

Each agent has a single responsibility. The orchestrator handles sequencing, records per-agent timing, and catches errors so that one failing agent cannot bring down the pipeline.

### The agents

**Intake Agent**  turns raw numbers into clinical meaning. Checks 30+ physiological thresholds (tachycardia, severe hypoxia, and so on), flags abnormalities, marks the dangerous ones as red flags, calculates a qSOFA sepsis screening score, and lists comorbidities. Roughly what a triage nurse does on arrival.

**Diagnostic Agent**  the core ML component. Feeds the structured intake data to a trained XGBoost classifier, which returns probabilities across ten acute conditions. Applies an acuity multiplier so higher-risk diagnoses such as septic shock and stroke are weighted slightly upward, making the system appropriately cautious. Runs SHAP to identify which features drove the top result. Returns a ranked differential of the five most likely conditions.

**Treatment Agent**  holds a knowledge base of clinical guidance (NICE, WHO, ESC, Surviving Sepsis Campaign) for all ten conditions. Matches the leading diagnosis to its guideline and personalises it: chronic kidney disease triggers a dose-adjustment warning, age over 75 triggers a frailty assessment flag.

**Liaison Agent**  produces the human-facing output. Generates a clinical narrative via the Claude API, with a deterministic template fallback so the system runs fully offline when no API key is present. Also produces the counterfactual explanation and trust score.

---

## Tech stack

- **Python**
- **XGBoost**  multi-class diagnosis ranking over 24 vital-sign and laboratory features
- **SHAP**  feature attribution for explainability
- **Flask**  web server and dashboard
- **Claude API** (Anthropic)  clinical narrative generation, optional

---

## Getting started

```bash
git clone https://github.com/ve7han/careagent-clinical-decision-support.git
cd careagent-clinical-decision-support

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

The trained model and SHAP explainer are included, so no training step is needed. To retrain from scratch:

```bash
python models/trainer.py
```

This generates 3,000 synthetic patients, trains the XGBoost classifier, builds the SHAP explainer, and saves both to `models/`.

Run the application:

```bash
python app.py
```

Open `http://localhost:5000`. Enter vitals manually or select one of three built-in demo patients: a classic sepsis presentation, a myocardial infarction, and a diabetic ketoacidosis case.

### Optional: Claude narrative generation

Without an API key the system uses its template fallback and works normally. To enable generated narratives, set:

```bash
export ANTHROPIC_API_KEY=your_key_here
```

---

## Project structure

```
data/
  mimic_simulator.py      synthetic patient generator
models/
  trainer.py              training script
  careagent_model.pkl     trained XGBoost classifier
  shap_explainer.pkl      fitted SHAP explainer
agents/
  orchestrator.py         pipeline coordination, timing, error isolation
  intake_agent.py         vitals screening, qSOFA, comorbidities
  diagnostic_agent.py     XGBoost inference + SHAP attribution
  treatment_agent.py      guideline matching and personalisation
  liaison_agent.py        narrative, counterfactual, trust score
templates/
  index.html              dashboard
app.py                    Flask server
requirements.txt
```

---

## Data

MIMIC-III is a critical care database from MIT containing de-identified records from real ICU stays. Access requires credentialling and a data use agreement, which were not available for this project.

`data/mimic_simulator.py` generates synthetic patients instead. It encodes the typical vital-sign ranges, laboratory values and comorbidity patterns associated with each of ten conditions, and samples clinically plausible patients from those distributions.

This is a deliberate and clearly bounded limitation. The synthetic data reproduces the statistical shape of real presentations but not their full complexity  no missing values, no measurement noise, no atypical presentations, no comorbidity interactions beyond those explicitly modelled. Reported model performance reflects the simulator, not clinical reality.

---

## Limitations

- **Not a clinical tool.** This is an academic demonstration. It has not been validated on real patients and must not be used for clinical decision-making.
- **Synthetic training data.** See above. Performance on real patient data is unknown.
- **Ten conditions only.** A real differential is open-ended; this is a closed-set classification problem.
- **No temporal reasoning.** The system sees a single snapshot, not a trajectory. Deterioration over time is often the most informative clinical signal.
- **Guideline knowledge base is static**, hardcoded rather than retrieved from live sources, and may not reflect current versions.

---

## What I would do differently

The most interesting limitation is the closed-set assumption. Framing diagnosis as a choice between ten labels makes the problem tractable and makes SHAP easy to apply, but it means the system is confidently wrong about anything outside its label set rather than expressing uncertainty. An abstention mechanism  returning "insufficient information" rather than a forced ranking  would be more honest and more clinically useful.

---

## Credits

MSc group project, Northumbria University London.

My contribution: the orchestrator  the agent pipeline, per-step timing, and the error isolation that keeps a single agent failure from bringing down the run — plus work on the SHAP explainability integration in the diagnostic agent.
