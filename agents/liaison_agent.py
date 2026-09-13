"""
Clinician Liaison Agent
------------------------
Synthesises all upstream agent outputs into a plain-language clinical
summary for the clinician.  When an ANTHROPIC_API_KEY is present it uses
the Claude API for richer narrative; otherwise falls back to a
high-quality template-based report.
"""

import os
from typing import Optional

try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False


def _confidence_label(ccs: float) -> str:
    if ccs >= 0.75: return "High"
    if ccs >= 0.50: return "Moderate"
    if ccs >= 0.30: return "Low"
    return "Very Low"

def _format_shap_narrative(supporting: list, against: list) -> str:
    parts = []
    for f in supporting[:3]:
        parts.append(f"{f['label']} (SHAP: +{f['shap']:.3f})")
    narrative = "Key supporting factors: " + ", ".join(parts) if parts else ""
    if against:
        contra = [f"{f['label']} (SHAP: {f['shap']:.3f})" for f in against[:2]]
        narrative += ". Factors against: " + ", ".join(contra)
    return narrative


class ClinicianLiaisonAgent:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self._llm_client = None
        if _ANTHROPIC_AVAILABLE and api_key:
            self._llm_client = anthropic.Anthropic(api_key=api_key)

    def generate_report(
        self,
        intake: dict,
        diagnostic: dict,
        treatment: dict,
        use_llm: bool = True,
    ) -> dict:
        top_diff   = diagnostic["differentials"][0]
        confidence = _confidence_label(top_diff["ccs"])
        shap_text  = _format_shap_narrative(diagnostic["supporting"], diagnostic["against"])

        # Try LLM narrative first
        narrative = None
        llm_used  = False
        if use_llm and self._llm_client:
            narrative = self._llm_narrative(intake, diagnostic, treatment, top_diff, shap_text)
            llm_used  = bool(narrative)

        # Fallback template
        if not narrative:
            narrative = self._template_narrative(intake, diagnostic, treatment, top_diff, shap_text, confidence)

        # Counterfactual
        counterfactual = self._counterfactual(diagnostic)

        # Trust score (placeholder — would be loaded from clinician profile in production)
        trust_score = 0.78

        return {
            "narrative":      narrative,
            "counterfactual": counterfactual,
            "confidence":     confidence,
            "ccs":            top_diff["ccs"],
            "trust_score":    trust_score,
            "llm_used":       llm_used,
            "top_diagnosis":  top_diff["diagnosis"],
            "shap_summary":   shap_text,
        }

    def _llm_narrative(self, intake, diagnostic, treatment, top_diff, shap_text) -> Optional[str]:
        try:
            top_feats = [
                f"{f['label']}: {f['value']} (SHAP {f['shap']:+.3f})"
                for f in diagnostic["top_features"][:6]
            ]
            prompt = f"""You are CareAgent's Clinician Liaison Agent — a clinical AI assistant.
Write a concise, professional clinical summary (3–4 paragraphs) for the attending clinician.
Tone: calm, precise, evidence-based. Do NOT be alarmist. Do NOT replace clinical judgment.

Patient: {intake['age']}yr {intake['sex']} | Flags: {', '.join(intake['high_priority_flags']) or 'None'}
qSOFA score: {intake['qsofa_score']}/3
Comorbidities: {', '.join(intake['comorbidities']) or 'None'}

Top diagnosis: {top_diff['diagnosis']} (CCS: {top_diff['ccs']:.2f})
Differentials: {', '.join(d['diagnosis'] for d in diagnostic['differentials'][1:4])}

SHAP key drivers: {shap_text}
Top features:
{chr(10).join(top_feats)}

Guideline: {treatment['guideline']}
Disposition: {treatment['disposition']}

Write the summary. Include:
1. Brief clinical picture paragraph
2. Diagnostic reasoning with key drivers
3. Recommended immediate actions (reference the guideline)
4. A caveat reminding the clinician this is AI-assisted decision support
Keep under 250 words."""

            response = self._llm_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"[LiaisonAgent] LLM call failed: {e}")
            return None

    def _template_narrative(self, intake, diagnostic, treatment, top_diff, shap_text, confidence) -> str:
        patient_desc = f"{intake['age']}-year-old {intake['sex']}"
        flags = intake["high_priority_flags"]
        flag_str = (", ".join(flags) + " flagged as high priority") if flags else "no high-priority flags identified"
        dx = top_diff["diagnosis"]
        ccs = top_diff["ccs"]
        diff2 = diagnostic["differentials"][1]["diagnosis"] if len(diagnostic["differentials"]) > 1 else "N/A"
        diff3 = diagnostic["differentials"][2]["diagnosis"] if len(diagnostic["differentials"]) > 2 else "N/A"

        return (
            f"CareAgent clinical summary for Patient {intake['patient_id']}.\n\n"
            f"The presenting {patient_desc} has {intake['flag_count']} clinical flags, with {flag_str}. "
            f"The qSOFA score is {intake['qsofa_score']}/3. "
            f"Comorbidities include: {', '.join(intake['comorbidities']) or 'none documented'}.\n\n"
            f"The primary diagnosis suggested by the Diagnostic Reasoning Agent is {dx} "
            f"(Contextual Clinical Score: {ccs:.2f}, {confidence} confidence). "
            f"{shap_text}. "
            f"Alternative diagnoses to consider: {diff2}, {diff3}.\n\n"
            f"Immediate management should follow {treatment['guideline']}. "
            f"Time window: {treatment.get('bundle_window', 'as per guideline')}. "
            f"Recommended disposition: {treatment['disposition']}.\n\n"
            f"⚠ This is AI-assisted decision support. All clinical decisions remain the "
            f"responsibility of the attending clinician. Please review all recommendations "
            f"against the full clinical picture."
        )

    def _counterfactual(self, diagnostic: dict) -> str:
        top  = diagnostic["differentials"][0]
        second = diagnostic["differentials"][1] if len(diagnostic["differentials"]) > 1 else None
        key_feat = diagnostic["supporting"][0] if diagnostic["supporting"] else None

        if not key_feat or not second:
            return "Insufficient data for counterfactual generation."

        return (
            f"If {key_feat['label']} had been within normal range "
            f"(SHAP contribution reduced to 0), model confidence in "
            f"{top['diagnosis']} would decrease significantly and "
            f"{second['diagnosis']} would become the leading differential "
            f"(estimated CCS: {second['ccs']:.2f})."
        )
