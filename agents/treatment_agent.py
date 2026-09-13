"""
Treatment Planner Agent
------------------------
Matches the top differential diagnosis to a structured clinical guideline
knowledge base (NICE / WHO / Surviving Sepsis Campaign) and returns a
personalised, evidence-based care pathway.
"""

# ── Guideline Knowledge Base ─────────────────────────────────────────────────
# Each entry: immediate, investigations, treatments, monitoring, disposition
GUIDELINES = {
    "Sepsis": {
        "guideline": "NICE NG51 — Sepsis: Recognition, Diagnosis and Early Management",
        "source":    "https://www.nice.org.uk/guidance/ng51",
        "time_critical": True,
        "bundle_window": "1 hour (Hour-1 Bundle)",
        "immediate": [
            "Obtain two sets of blood cultures (peripheral) before antibiotics",
            "Measure serum lactate — repeat if >2 mmol/L",
            "Administer IV broad-spectrum antibiotics within 60 minutes",
            "IV fluid resuscitation: 30 ml/kg crystalloid bolus if lactate ≥2 or hypotensive",
            "Apply high-flow oxygen via non-rebreather mask — target SpO₂ ≥94%",
        ],
        "investigations": [
            "FBC, CRP, Procalcitonin, Coagulation screen (PT/INR, APTT)",
            "U&E, LFTs, Glucose, Lactate",
            "Blood cultures ×2, Urine MC&S, Sputum culture if productive cough",
            "Urinalysis + urine output monitoring (target >0.5 ml/kg/hr)",
            "Chest X-ray",
        ],
        "treatments": [
            "Piperacillin-tazobactam 4.5g IV Q8H (adjust if penicillin allergy)",
            "Consider adding Gentamicin if organ dysfunction or no improvement at 1h",
            "Noradrenaline vasopressor if MAP <65 mmHg after fluid resuscitation",
            "Hydrocortisone 200mg/day IV if refractory shock",
        ],
        "monitoring": [
            "Continuous cardiac monitoring (ECG, SpO₂, RR)",
            "Urine output hourly — catheterise if septic shock",
            "Repeat lactate at 2 hours — target clearance >10%",
            "Reassess antibiotic appropriateness at 48–72 hours (de-escalate)",
            "Daily organ function assessment: U&E, LFTs, FBC",
        ],
        "disposition": "ICU or HDU — escalate immediately if organ dysfunction present",
    },

    "Septic Shock": {
        "guideline": "Surviving Sepsis Campaign Guidelines 2021",
        "source":    "https://www.sccm.org/SurvivingSepsisCampaign",
        "time_critical": True,
        "bundle_window": "Immediate — RICU/ICU transfer",
        "immediate": [
            "Emergency ICU/RICU transfer — this is immediately life-threatening",
            "Large-bore IV access ×2 + arterial line for continuous BP monitoring",
            "Vasopressor support: Noradrenaline as first-line, target MAP ≥65 mmHg",
            "Blood cultures before antibiotics — do not delay antibiotics for cultures",
            "Broad-spectrum IV antibiotics within 30 minutes",
            "Aggressive fluid resuscitation: 30 ml/kg IV crystalloid, reassess after",
        ],
        "investigations": [
            "Arterial blood gas (ABG) — assess pH, pCO₂, lactate",
            "Echocardiogram (POCUS or formal) — assess cardiac function and preload",
            "FBC, Coagulation screen, D-Dimer, Fibrinogen (assess DIC)",
            "Procalcitonin, CRP, Blood cultures ×2",
            "Urine output monitoring — catheterise immediately",
        ],
        "treatments": [
            "Noradrenaline 0.01–3.3 mcg/kg/min — titrate to MAP ≥65",
            "Add Vasopressin 0.03 U/min if noradrenaline >0.25 mcg/kg/min",
            "Meropenem 1g IV Q8H if high MDR organism risk",
            "IV Hydrocortisone 200mg/day if vasopressor refractory",
            "Lung-protective ventilation if ARDS develops (TV 6ml/kg, PEEP ≥5)",
        ],
        "monitoring": [
            "Continuous arterial line BP + SpO₂ + ECG",
            "Central venous pressure (CVP) monitoring",
            "Hourly urine output — target >0.5 ml/kg/hr",
            "Lactate q2h — target clearance >10% per 2h",
            "ScvO₂ via central line — target >70%",
        ],
        "disposition": "Immediate ICU admission — senior clinician bedside review required",
    },

    "Acute MI": {
        "guideline": "ESC Guidelines on Acute Coronary Syndromes 2023",
        "source":    "https://www.escardio.org/Guidelines",
        "time_critical": True,
        "bundle_window": "90 minutes door-to-balloon (STEMI)",
        "immediate": [
            "12-lead ECG within 10 minutes of presentation — interpret immediately",
            "Activate catheterisation lab if STEMI criteria met (door-to-balloon <90 min)",
            "IV access + bloods: Troponin T/I, FBC, U&E, Coagulation, Lipids, HbA1c",
            "Aspirin 300mg loading dose PO immediately",
            "P2Y12 inhibitor (Ticagrelor 180mg PO) — check contraindications",
            "Supplemental O₂ only if SpO₂ <90% (avoid hyperoxia)",
        ],
        "investigations": [
            "Serial Troponin T/I at 0h and 1h (hs-cTnT/I) or 3h",
            "ECG: serial recordings at 0, 30, 60 minutes",
            "Echocardiogram: assess LVEF and wall motion abnormalities",
            "Chest X-ray: pulmonary oedema, cardiac silhouette",
            "Angiography (PCI or diagnostic)",
        ],
        "treatments": [
            "Primary PCI preferred over thrombolysis for STEMI",
            "Fondaparinux 2.5mg SC daily (or UFH bolus for PCI)",
            "Beta-blocker (Metoprolol 25–50mg PO) if haemodynamically stable",
            "ACE inhibitor within 24h if tolerated (Ramipril 2.5mg BD)",
            "High-intensity statin (Atorvastatin 80mg) immediately",
            "GTN 0.4mg sublingual/spray if BP allows, for pain relief",
        ],
        "monitoring": [
            "Continuous ECG telemetry for minimum 24 hours",
            "Serial troponin measurements",
            "Daily electrolytes, renal function, glucose",
            "BP and HR monitoring — aim HR 60–70 bpm",
            "Repeat echocardiogram at 48–72h to assess LVEF",
        ],
        "disposition": "Coronary Care Unit (CCU) — cardiology team primary management",
    },

    "Heart Failure": {
        "guideline": "ESC Heart Failure Guidelines 2021 / NICE NG106",
        "source":    "https://www.nice.org.uk/guidance/ng106",
        "time_critical": False,
        "bundle_window": "Within 60 minutes for acute decompensation",
        "immediate": [
            "Sit patient upright — legs dependent to reduce preload",
            "High-flow oxygen if SpO₂ <90%; consider CPAP/BiPAP for severe APO",
            "IV Furosemide 40–80mg bolus — titrate based on urine output response",
            "IV Glyceryl Trinitrate infusion if SBP >90 mmHg (venodilator)",
            "Bloods: BNP/NT-proBNP, Troponin, U&E, FBC, LFTs, TFTs",
        ],
        "investigations": [
            "BNP or NT-proBNP — key diagnostic and prognostic marker",
            "Echocardiogram: LVEF, valvular disease, diastolic function",
            "ECG: LVH, AF, ischaemic changes",
            "Chest X-ray: cardiomegaly, pulmonary oedema (bat-wing pattern)",
            "Urine output monitoring hourly — target >1 ml/kg/hr with diuresis",
        ],
        "treatments": [
            "IV Furosemide infusion 5–10mg/hr if inadequate bolus response",
            "ACE inhibitor or ARB (if not already prescribed)",
            "Beta-blocker — do NOT initiate during acute decompensation",
            "Spironolactone 25–50mg if persistent fluid overload",
            "Consider Digoxin if AF with rapid ventricular rate",
        ],
        "monitoring": [
            "Daily weight (target 0.5–1 kg loss per day)",
            "Strict fluid balance chart",
            "Urea and electrolytes (U&E) daily — risk of diuretic-induced hypokalaemia",
            "Daily chest auscultation — assess crepitations",
            "BNP/NT-proBNP on discharge for baseline",
        ],
        "disposition": "Medical ward with cardiac monitoring — escalate to CCU if haemodynamically unstable",
    },

    "Pneumonia": {
        "guideline": "BTS Guidelines on Community-Acquired Pneumonia 2019 / NICE NG138",
        "source":    "https://www.brit-thoracic.org.uk",
        "time_critical": False,
        "bundle_window": "4 hours from presentation",
        "immediate": [
            "Calculate CURB-65 score (Confusion, Urea, RR, BP, Age ≥65)",
            "Oxygen therapy: target SpO₂ 94–98% (88–92% if COPD risk)",
            "Blood cultures before antibiotics if CURB-65 ≥2",
            "Sputum culture and sensitivity if productive cough",
            "Urine Legionella antigen and Streptococcus pneumoniae antigen (severe CAP)",
        ],
        "investigations": [
            "CURB-65 score: 0–1 home, 2 hospital, 3–5 HDU/ICU",
            "FBC, CRP, U&E, LFTs, blood cultures",
            "Chest X-ray PA: lobar consolidation, infiltrates",
            "ABG if SpO₂ persistently <94% or RR >30",
            "CT Thorax if atypical presentation or poor response to antibiotics",
        ],
        "treatments": [
            "CURB-65 0–1: Co-amoxiclav 625mg PO TDS + Clarithromycin 500mg PO BD",
            "CURB-65 2: Co-amoxiclav 1.2g IV TDS + Clarithromycin 500mg IV BD",
            "CURB-65 ≥3 (Severe CAP): Piperacillin-tazobactam 4.5g IV Q8H + Clarithromycin IV",
            "Consider Oseltamivir if influenza suspected (RDT or nasopharyngeal swab)",
            "VTE prophylaxis: LMWH unless contraindicated",
        ],
        "monitoring": [
            "Continuous SpO₂ monitoring",
            "RR, HR, BP Q4H",
            "Temperature Q6H — expect defervescence within 72h",
            "CRP at 48–72h — if not falling, consider alternative diagnosis or organism",
            "Chest X-ray at 4–6 weeks post-discharge to confirm resolution",
        ],
        "disposition": "CURB-65 ≥2: hospital admission; ≥3: HDU/ICU consideration",
    },

    "AKI": {
        "guideline": "NICE NG148 — Acute Kidney Injury in Adults",
        "source":    "https://www.nice.org.uk/guidance/ng148",
        "time_critical": False,
        "bundle_window": "AKI bundle within 6 hours of recognition",
        "immediate": [
            "Identify and treat underlying cause (sepsis, dehydration, nephrotoxins)",
            "Stop nephrotoxic medications: NSAIDs, ACE inhibitors, aminoglycosides, contrast",
            "IV fluid challenge if pre-renal AKI: 500ml 0.9% NaCl over 15 minutes",
            "Urinary catheter: strict hourly urine output monitoring",
            "Treat hyperkalaemia urgently if K⁺ >6.0 or ECG changes present",
        ],
        "investigations": [
            "U&E, creatinine, eGFR (compare with baseline if available)",
            "Urine: dipstick, MC&S, Bence-Jones protein, protein:creatinine ratio",
            "Renal USS if obstruction suspected",
            "ABG: assess acidosis (AKI commonly causes metabolic acidosis)",
            "ANCA, anti-GBM, complement if glomerulonephritis suspected",
        ],
        "treatments": [
            "Treat hyperkalaemia: Calcium gluconate 10ml 10% IV (stabilise membrane)",
            "Insulin-dextrose: 10 units Actrapid + 50ml 50% dextrose IV",
            "Sodium bicarbonate if severe metabolic acidosis (pH <7.1)",
            "Renal replacement therapy if anuric, severe hyperkalaemia, or refractory acidosis",
            "Dose-adjust all renally cleared medications",
        ],
        "monitoring": [
            "Urine output hourly — target >0.5 ml/kg/hr",
            "U&E and creatinine Q12H until stabilised",
            "Daily fluid balance — avoid overload",
            "ECG monitoring if K⁺ >5.5",
            "Nephrology review within 24h for Stage 2 or 3 AKI",
        ],
        "disposition": "Medical ward or renal unit; ICU if Stage 3 AKI with organ dysfunction",
    },

    "Pulmonary Embolism": {
        "guideline": "ESC Guidelines on Pulmonary Embolism 2019 / NICE NG158",
        "source":    "https://www.nice.org.uk/guidance/ng158",
        "time_critical": True,
        "bundle_window": "Risk-stratify immediately (PESI score)",
        "immediate": [
            "Calculate Wells PE score — if ≥4 or high probability, treat empirically",
            "D-Dimer: if Wells <4 and D-Dimer negative, PE effectively excluded",
            "CT Pulmonary Angiography (CTPA) — gold standard if D-Dimer positive or high pretest",
            "Oxygen supplementation: target SpO₂ ≥94%",
            "IV access + anticoagulation: LMWH (Enoxaparin 1.5mg/kg SC OD) or UFH",
        ],
        "investigations": [
            "CTPA — confirm diagnosis and assess clot burden",
            "ECG: sinus tachycardia (commonest), S1Q3T3, RBBB, AF",
            "Echocardiogram: right heart strain (RV dilatation, McConnell sign)",
            "Troponin + BNP: prognostication markers",
            "Lower limb Doppler USS: confirm concurrent DVT",
        ],
        "treatments": [
            "Massive PE with haemodynamic compromise: Thrombolysis (Alteplase 100mg IV over 2h)",
            "Sub-massive PE: LMWH anticoagulation ± catheter-directed thrombolysis",
            "DOAC (Rivaroxaban or Apixaban) for non-massive PE — 21 days then maintenance",
            "IVC filter if absolute contraindication to anticoagulation",
            "Oxygen and haemodynamic support as needed",
        ],
        "monitoring": [
            "Continuous SpO₂ + ECG telemetry",
            "BP Q1H if haemodynamically unstable",
            "Repeat ECHO at 24–48h if RV dysfunction on admission",
            "Anti-Xa levels if UFH or renal impairment with LMWH",
            "Outpatient follow-up: thrombophilia screen, cancer screening (unprovoked PE)",
        ],
        "disposition": "Medical ward; ICU if massive PE or haemodynamic instability",
    },

    "Stroke": {
        "guideline": "NICE NG128 — Stroke and TIA / RCP National Clinical Guideline",
        "source":    "https://www.nice.org.uk/guidance/ng128",
        "time_critical": True,
        "bundle_window": "4.5 hours for thrombolysis; <24h for thrombectomy",
        "immediate": [
            "FAST assessment — Face drooping, Arm weakness, Speech difficulty, Time to call",
            "Non-contrast CT Head immediately — exclude haemorrhage before thrombolysis",
            "If ischaemic stroke confirmed and within 4.5h: Alteplase 0.9mg/kg IV (max 90mg)",
            "Blood glucose: treat hypoglycaemia immediately if <3 mmol/L",
            "Admit to acute stroke unit — do NOT give anticoagulants in first 24h post-thrombolysis",
        ],
        "investigations": [
            "CT Head ± CT Angiography (large vessel occlusion — thrombectomy candidate)",
            "MRI Brain DWI if CT non-diagnostic or posterior fossa stroke suspected",
            "ECG + 24h cardiac monitoring — detect AF",
            "FBC, Coagulation (INR), U&E, Lipids, HbA1c, Blood glucose",
            "Carotid Doppler USS if anterior circulation stroke",
        ],
        "treatments": [
            "Thrombectomy: if large vessel occlusion within 24h of onset — specialist centre",
            "Aspirin 300mg PO/PR after 24h if no haemorrhage, continue for 2 weeks",
            "Dual antiplatelet (Aspirin + Clopidogrel) for minor stroke/TIA for 21 days",
            "Statin (Atorvastatin 80mg) for ischaemic stroke regardless of cholesterol",
            "Anticoagulation for AF-related stroke: start within 2 weeks (DOAC preferred)",
        ],
        "monitoring": [
            "Neurological observations Q1H for first 24h (GCS, pupils, focal deficits)",
            "Blood glucose Q6H — maintain 6–10 mmol/L",
            "Swallowing assessment before any oral intake (SALT referral)",
            "BP monitoring — avoid aggressive reduction in acute phase",
            "Daily neurological assessment — use NIHSS score",
        ],
        "disposition": "Acute stroke unit — hyperacute phase (HASU) if large vessel occlusion",
    },

    "DKA": {
        "guideline": "JBDS DKA Guidelines 2023 / NICE NG17",
        "source":    "https://www.diabetes.org.uk/professionals/position-statements-reports/specialist-care-for-children-and-adults-and-complications/the-management-of-diabetic-ketoacidosis-in-adults",
        "time_critical": True,
        "bundle_window": "Fixed-rate insulin infusion within 1 hour",
        "immediate": [
            "Confirm DKA: Glucose >11mmol/L, Ketones >3mmol/L or pH <7.3 / HCO₃ <15",
            "IV 0.9% NaCl: 1L over 1h → 1L over 2h → 1L over 4h → guided by fluid balance",
            "Fixed-rate IV insulin infusion (FRIII): 0.1 units/kg/hr",
            "IV KCl replacement: guided by K⁺ level (do NOT give if K⁺ >5.5)",
            "NG tube if reduced consciousness or vomiting",
        ],
        "investigations": [
            "Capillary glucose Q1H until stable",
            "Capillary ketones Q1–2H (target clearance <0.5 mmol/L/hr)",
            "ABG/VBG Q2H: monitor pH, HCO₃ and pCO₂",
            "U&E Q2–4H: especially potassium (shifts rapidly with insulin)",
            "FBC, CRP, blood cultures, urine MC&S (identify precipitating infection)",
        ],
        "treatments": [
            "Transition to SC insulin when: ketones <0.6, patient eating and drinking, pH >7.3",
            "Continue long-acting insulin throughout (do NOT stop basal insulin)",
            "Treat precipitating cause (infection: antibiotics; missed insulin: review regimen)",
            "Phosphate replacement if severe hypophosphataemia (<0.5 mmol/L)",
            "VTE prophylaxis: LMWH once dehydration corrected",
        ],
        "monitoring": [
            "Glucose Q1H during FRIII",
            "Ketones Q1–2H — resolution criteria: <0.6 mmol/L",
            "U&E Q2H for first 6h — hypokalaemia is major risk",
            "Urine output Q1H — catheterise if oliguric",
            "Fluid balance chart — cumulative input and output",
        ],
        "disposition": "Medical ward (DKA pathway); HDU/ICU if pH <7.0 or reduced consciousness",
    },

    "COPD Exacerbation": {
        "guideline": "GOLD COPD Guidelines 2024 / BTS COPD Guideline",
        "source":    "https://goldcopd.org/2024-gold-report/",
        "time_critical": False,
        "bundle_window": "Controlled oxygen within 30 minutes",
        "immediate": [
            "Controlled oxygen: target SpO₂ 88–92% (risk of hypercapnic drive suppression)",
            "Salbutamol 5mg nebulised Q20 min for first hour, then Q4–6H PRN",
            "Ipratropium bromide 500mcg nebulised Q6H",
            "Prednisolone 30–40mg PO or Hydrocortisone 100mg IV for 5 days",
            "Consider non-invasive ventilation (NIV/BiPAP) if pH <7.35 and pCO₂ >6.0",
        ],
        "investigations": [
            "ABG: confirm type II respiratory failure (↑pCO₂, ↓pH, ↑HCO₃)",
            "Chest X-ray: exclude pneumothorax, consolidation, effusion",
            "FBC, CRP, U&E — guide antibiotic decision",
            "ECG: right heart strain, AF, arrhythmia",
            "Sputum culture if purulent — guide antibiotic de-escalation",
        ],
        "treatments": [
            "Antibiotics if purulent sputum: Co-amoxiclav 625mg TDS or Doxycycline 100mg OD",
            "NIV: BiPAP settings 14/4 cmH₂O IPAP/EPAP — titrate to clinical response",
            "Intubation and ventilation if NIV fails (pH <7.26 despite NIV)",
            "VTE prophylaxis: LMWH",
            "Refer to pulmonary rehabilitation if appropriate (post-acute phase)",
        ],
        "monitoring": [
            "ABG at 30–60 minutes after oxygen therapy initiation",
            "SpO₂ continuous monitoring — do not exceed 92%",
            "RR, HR, BP Q4H",
            "Repeat ABG if NIV initiated — within 1h",
            "CRP at 48h — guide antibiotic duration",
        ],
        "disposition": "Medical ward with respiratory support; HDU if NIV required or pH <7.3",
    },
}


class TreatmentPlannerAgent:
    def plan(self, top_diagnosis: str, patient_summary: dict) -> dict:
        guideline = GUIDELINES.get(top_diagnosis, None)

        if guideline is None:
            return {
                "diagnosis": top_diagnosis,
                "guideline": "No specific guideline available",
                "source": "",
                "time_critical": False,
                "bundle_window": "",
                "immediate": ["Refer to specialist for management"],
                "investigations": [],
                "treatments": [],
                "monitoring": [],
                "disposition": "Discuss with senior clinician",
            }

        # Personalise based on patient flags
        notes = _personalise(top_diagnosis, patient_summary, guideline)

        return {
            "diagnosis":      top_diagnosis,
            "guideline":      guideline["guideline"],
            "source":         guideline["source"],
            "time_critical":  guideline["time_critical"],
            "bundle_window":  guideline.get("bundle_window", ""),
            "immediate":      guideline["immediate"],
            "investigations": guideline["investigations"],
            "treatments":     guideline["treatments"],
            "monitoring":     guideline["monitoring"],
            "disposition":    guideline["disposition"],
            "personalised_notes": notes,
        }


def _personalise(diagnosis: str, intake: dict, guideline: dict) -> list:
    notes = []
    raw = intake.get("raw", {})

    if raw.get("ckd"):
        notes.append("CKD noted: dose-adjust renally cleared drugs. Avoid NSAIDs and contrast agents. Nephrology input recommended.")
    if raw.get("diabetes"):
        notes.append("Diabetes: monitor blood glucose Q4H. Stress hyperglycaemia common — target 6–10 mmol/L with sliding scale insulin if needed.")
    if raw.get("cad"):
        notes.append("Known CAD: ensure cardiology review. Avoid medications that reduce preload/afterload if haemodynamically unstable.")
    if raw.get("age", 0) > 75:
        notes.append("Age >75: frailty assessment recommended. Consider reduced drug doses. Early involvement of care of the elderly team.")
    if diagnosis in ("Sepsis", "Septic Shock") and not raw.get("recent_infection"):
        notes.append("Source control: no clear infection source identified — ensure cultures from all sites (blood ×2, urine, sputum). Consider imaging (CT chest/abdomen) to identify occult focus.")
    if raw.get("potassium", 4) > 5.5:
        notes.append("Hyperkalaemia present: avoid potassium-containing IV fluids. Treat per AKI hyperkalaemia protocol if K⁺ >6.0.")
    if raw.get("troponin", 0) > 0.5 and diagnosis not in ("Acute MI",):
        notes.append("Elevated troponin in non-cardiac primary diagnosis — Type 2 MI / demand ischaemia possible. Cardiology input recommended.")

    return notes
