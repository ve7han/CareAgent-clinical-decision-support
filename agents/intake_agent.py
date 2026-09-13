"""
Patient Intake Agent
--------------------
Parses a raw patient record (dict / simulated FHIR JSON),
computes derived flags, and returns a structured clinical summary
ready for the Diagnostic Reasoning Agent.
"""

from typing import Any

# Clinical flag thresholds (evidence-based)
FLAGS = {
    "Tachycardia":           lambda r: r["heart_rate"] > 100,
    "Bradycardia":           lambda r: r["heart_rate"] < 50,
    "Hypotension":           lambda r: r["systolic_bp"] < 90,
    "Hypertensive Crisis":   lambda r: r["systolic_bp"] > 180,
    "Tachypnoea":            lambda r: r["respiratory_rate"] > 20,
    "Hypoxia":               lambda r: r["spo2"] < 94,
    "Severe Hypoxia":        lambda r: r["spo2"] < 88,
    "Fever":                 lambda r: r["temperature"] > 38.3,
    "Hypothermia":           lambda r: r["temperature"] < 36.0,
    "Leukocytosis":          lambda r: r["wbc"] > 12.0,
    "Leukopenia":            lambda r: r["wbc"] < 4.0,
    "Elevated Lactate":      lambda r: r["lactate"] > 2.0,
    "Severe Lactataemia":    lambda r: r["lactate"] > 4.0,
    "AKI (Creatinine)":      lambda r: r["creatinine"] > 1.5,
    "Elevated Troponin":     lambda r: r["troponin"] > 0.04,
    "High Troponin":         lambda r: r["troponin"] > 1.0,
    "Elevated CRP":          lambda r: r["crp"] > 100,
    "Hyperglycaemia":        lambda r: r["glucose"] > 11.0,
    "Hypoglycaemia":         lambda r: r["glucose"] < 3.9,
    "Hyperkalaemia":         lambda r: r["potassium"] > 5.5,
    "Hypokalaemia":          lambda r: r["potassium"] < 3.5,
    "Hyponatraemia":         lambda r: r["sodium"] < 133,
    "Thrombocytopaenia":     lambda r: r["platelets"] < 100,
    "Anaemia":               lambda r: r["haemoglobin"] < 10.0,
    "Elevated Bilirubin":    lambda r: r["bilirubin"] > 1.5,
    "Liver Injury (ALT)":    lambda r: r["alt"] > 80,
    "Recent Infection":      lambda r: bool(r.get("recent_infection", 0)),
    "Diabetes":              lambda r: bool(r.get("diabetes", 0)),
    "Hypertension Hx":       lambda r: bool(r.get("hypertension", 0)),
    "CKD":                   lambda r: bool(r.get("ckd", 0)),
    "CAD":                   lambda r: bool(r.get("cad", 0)),
}

# Priority flags (shown prominently)
HIGH_PRIORITY = {
    "Severe Hypoxia", "Severe Lactataemia", "Hypotension",
    "High Troponin", "Hypoglycaemia", "Thrombocytopaenia",
    "Hypertensive Crisis",
}

FEATURE_UNITS = {
    "heart_rate":       ("bpm",    0),
    "systolic_bp":      ("mmHg",   0),
    "diastolic_bp":     ("mmHg",   0),
    "respiratory_rate": ("/min",   0),
    "spo2":             ("%",      1),
    "temperature":      ("°C",     1),
    "wbc":              ("×10⁹/L", 1),
    "lactate":          ("mmol/L", 1),
    "creatinine":       ("mg/dL",  2),
    "troponin":         ("ng/mL",  2),
    "crp":              ("mg/L",   0),
    "sodium":           ("mmol/L", 0),
    "potassium":        ("mmol/L", 1),
    "glucose":          ("mmol/L", 1),
    "haemoglobin":      ("g/dL",   1),
    "platelets":        ("×10⁹/L", 0),
    "alt":              ("U/L",    0),
    "bilirubin":        ("mg/dL",  1),
    "age":              ("yrs",    0),
}

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
}


class PatientIntakeAgent:
    def process(self, record: dict) -> dict:
        flags = []
        high_priority_flags = []
        for flag_name, check_fn in FLAGS.items():
            try:
                if check_fn(record):
                    entry = {"flag": flag_name, "priority": flag_name in HIGH_PRIORITY}
                    flags.append(entry)
                    if flag_name in HIGH_PRIORITY:
                        high_priority_flags.append(flag_name)
            except (KeyError, TypeError):
                pass

        # Format vitals display
        vitals = {}
        for feat, (unit, decimals) in FEATURE_UNITS.items():
            if feat in record:
                val = record[feat]
                label = FEATURE_LABELS.get(feat, feat)
                vitals[feat] = {
                    "label": label,
                    "value": round(float(val), decimals),
                    "unit":  unit,
                    "display": f"{round(float(val), decimals)} {unit}",
                }

        comorbidities = []
        if record.get("diabetes"):       comorbidities.append("Diabetes Mellitus")
        if record.get("hypertension"):   comorbidities.append("Hypertension")
        if record.get("ckd"):            comorbidities.append("Chronic Kidney Disease")
        if record.get("cad"):            comorbidities.append("Coronary Artery Disease")
        if record.get("recent_infection"):comorbidities.append("Recent Infection")

        # qSOFA score (sepsis screening)
        qsofa = 0
        if record.get("systolic_bp", 120) <= 100: qsofa += 1
        if record.get("respiratory_rate", 16) >= 22: qsofa += 1
        # GCS proxy: assume alert unless high lactate or hypoxia
        if record.get("lactate", 1) > 3.0: qsofa += 1
        qsofa = min(qsofa, 3)

        return {
            "patient_id":          record.get("patient_id", "UNKNOWN"),
            "sex":                 record.get("sex", "Unknown"),
            "age":                 int(record.get("age", 0)),
            "vitals":              vitals,
            "flags":               flags,
            "high_priority_flags": high_priority_flags,
            "flag_count":          len(flags),
            "comorbidities":       comorbidities,
            "qsofa_score":         qsofa,
            "raw":                 record,
        }
