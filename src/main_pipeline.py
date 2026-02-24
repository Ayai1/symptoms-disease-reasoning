"""
Phase 6: Main Pipeline
Integrates all components for end-to-end diagnosis
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from ensemble_predictor import get_ensemble
from tree_of_thoughts import get_tot
from rag_probability_explainer import build_probability_explanation


def diagnose(user_input, age=None, sex=None, alpha=0.4, beta=0.6,
             top_k=5, min_score=0.1, min_matches=2):
    """
    Main diagnosis function
    """

    # --------------------------------------------------
    # Ensemble prediction
    # --------------------------------------------------
    ensemble = get_ensemble(alpha, beta)
    ranked = ensemble.predict(user_input, min_score, min_matches)

    # --------------------------------------------------
    # ⭐ Attach RAG probability justification (NEW)
    # --------------------------------------------------
    for d in ranked:
        try:
            d["literature_support"] = build_probability_explanation(
                d["disease"],
                d.get("matched_symptoms", [])
            )
        except Exception:
            d["literature_support"] = []

    # --------------------------------------------------
    # Tree of Thoughts
    # --------------------------------------------------
    tot = get_tot()
    tree = tot.build_tree_of_thoughts(ranked, top_k=min(top_k, len(ranked)))

    # --------------------------------------------------
    # Overall confidence calculation
    # --------------------------------------------------
    confidence = "low"

    if ranked:
        top = ranked[0]

        coverage = len(top["matched_symptoms"]) / (
            len(top["matched_symptoms"]) +
            len(top["missing_symptoms"]) + 1e-6
        )

        conf = top["confidence"]

        if conf >= 0.7 and coverage >= 0.6:
            confidence = "high"
        elif conf >= 0.4:
            confidence = "medium"
        else:
            confidence = "low"

    return {
        "diagnoses": ranked[:top_k],
        "tree": tree,
        "confidence": confidence,
        "num_symptoms": len(user_input)
    }


def get_diagnosis_summary(diagnosis_result):
    """
    Get a human-readable summary of diagnosis results
    """

    output = []
    output.append("=" * 80)
    output.append("DIAGNOSIS RESULTS")
    output.append("=" * 80)
    output.append(f"\nConfidence Level: {diagnosis_result['confidence'].upper()}")
    output.append(f"Number of symptoms provided: {diagnosis_result['num_symptoms']}")
    output.append(f"\nTop Diagnoses:")
    output.append("-" * 80)

    for i, diag in enumerate(diagnosis_result['diagnoses'], 1):
        output.append(f"\n{i}. {diag['disease']}")
        output.append(f"   Confidence: {diag['confidence']:.1%}")
        output.append(f"   Prior Support (RF): {diag.get('prior_support', 0):.1%}")
        output.append(f"   Evidence Score: {diag.get('evidence_score', 0):.1%}")
        output.append(f"   Matched Symptoms: {', '.join(diag['matched_symptoms'][:5])}")

        if len(diag['matched_symptoms']) > 5:
            output.append(f"   ... and {len(diag['matched_symptoms']) - 5} more")

    return "\n".join(output)