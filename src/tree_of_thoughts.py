import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from rule_based_scorer import get_scorer
from rag_signal_extractor import extract_rag_keywords


class TreeOfThoughts:
    """Tree-of-Thoughts reasoning for interactive diagnosis"""

    def __init__(self, dataset_path="dataset.csv", severity_path="Symptom-severity.csv"):
        """
        Initialize Tree-of-Thoughts system
        """
        self.scorer = get_scorer(dataset_path, severity_path)
        self.severity_map = self.scorer.severity_map

    # ---------------------------------------------------------
    # THOUGHT NODE
    # ---------------------------------------------------------
    def build_thought_node(self, disease_result):
        return {
    "disease": disease_result["disease"],
    "score": disease_result["confidence"],
    "matched": disease_result.get("matched_symptoms", []),
    "missing": disease_result.get("missing_symptoms", []),
    "asked": [],  
    "next_questions": [],
    "status": "open"
}
    # ---------------------------------------------------------
    # ⭐ RAG-GUIDED SYMPTOM SELECTION (NEW)
    # ---------------------------------------------------------
    def select_discriminative_symptoms(self, missing_symptoms, disease_name=None, top_n=2):
        """
        Select important missing symptoms using:
        - severity weights
        - RAG literature signals
        """

        if not missing_symptoms:
            return []

        # -------------------------
        # Severity score
        # -------------------------
        def severity_score(symptom):
            return self.severity_map.get(symptom, 1)

        # -------------------------
        # RAG keyword boost
        # -------------------------
        rag_terms = []
        if disease_name:
            try:
                rag_terms = extract_rag_keywords([disease_name.lower()])
            except Exception:
                rag_terms = []

        def rag_boost(symptom):
            s = symptom.replace("_"," ").lower()

            score = 0

            for r in rag_terms:
                # direct match
                if r in s:
                    score += 2

                # semantic hints (simple but effective)
                if "airway" in r and "breath" in s:
                    score += 1
                if "bronch" in r and ("wheez" in s or "sputum" in s):
                    score += 1
                if "ventilation" in r and "breath" in s:
                    score += 1

            return score

        # -------------------------
        # Combined ranking
        # -------------------------
        ranked = sorted(
            missing_symptoms,
            key=lambda s: (
                rag_boost(s),      # ⭐ literature signal
                severity_score(s)  # severity weight
            ),
            reverse=True
        )

        return ranked[:top_n]

    # ---------------------------------------------------------
    # FOLLOW-UP QUESTIONS
    # ---------------------------------------------------------
    def generate_followup_questions(self, thought, top_n=2):
   
    # Only ask about symptoms that are still missing
        remaining_missing = [
    s for s in thought["missing"]
    if s not in thought["matched"]
    and s not in thought.get("asked", [])
]

        key_symptoms = self.select_discriminative_symptoms(
        remaining_missing,
        disease_name=thought["disease"],
        top_n=top_n
    )

        questions = []
        for s in key_symptoms:
            question_text = s.replace("_", " ").lower()
            question_text = f"Do you have {question_text}?"

            questions.append({
            "symptom": s,
            "question": question_text,
            "purpose": "confirm_or_reject"
        })

        return questions

    # ---------------------------------------------------------
    # BUILD TREE
    # ---------------------------------------------------------
    def build_tree_of_thoughts(self, ranked_diseases, top_k=3, questions_per_disease=2):
        tree = []

        for disease_result in ranked_diseases[:top_k]:
            node = self.build_thought_node(disease_result)
            node["next_questions"] = self.generate_followup_questions(
                node,
                questions_per_disease
            )
            tree.append(node)

        return tree

    # ---------------------------------------------------------
    # UPDATE SINGLE THOUGHT
    # ---------------------------------------------------------
    def update_thought_with_answer(self, thought, symptom, answer):

        answer_lower = answer.lower().strip()
        if "asked" not in thought:
            thought["asked"] = []

        if symptom not in thought["asked"]:
            thought["asked"].append(symptom)

        if answer_lower in ["yes", "y", "true", "1"]:
            if symptom not in thought["matched"]:
                thought["matched"].append(symptom)

            if symptom in thought["missing"]:
                thought["missing"].remove(symptom)

            evidence_gain = self.severity_map.get(symptom, 1) / 10
            thought["score"] = min(1.0, thought["score"] + evidence_gain)

        elif answer_lower in ["no", "n", "false", "0"]:
            thought["score"] *= 0.6

        # prune weak thoughts
        if thought["score"] < 0.1:
            thought["status"] = "pruned"

        # recompute rule-based score
        normalized_symptoms = set(thought["matched"])
        score, matched, missing = self.scorer.score_disease(
            thought["disease"],
            normalized_symptoms
        )

        thought["score"] = round(min(0.9, max(thought["score"], score)), 3)
        thought["matched"] = matched
        thought["missing"] = missing

        return thought

    # ---------------------------------------------------------
    # UPDATE TREE
    # ---------------------------------------------------------
    def update_tree_with_answers(self, tree, answers):

        for thought in tree:
            if thought["status"] == "pruned":
                continue

            for symptom, answer in answers.items():
                if symptom in [q["symptom"] for q in thought["next_questions"]]:
                    self.update_thought_with_answer(thought, symptom, answer)

        tree.sort(key=lambda x: x["score"], reverse=True)
        for thought in tree:
            # regenerate fresh questions
            new_questions = self.generate_followup_questions(thought)

        # remove already-answered symptoms
            asked = set(answers.keys())

            thought["next_questions"] = [
                q for q in new_questions if q["symptom"] not in asked
            ]
        return tree

    # ---------------------------------------------------------
    # GET NEXT QUESTIONS
    # ---------------------------------------------------------
    def get_next_questions(self, tree, max_questions=3):

        if not tree:
            return []
        tree = sorted(tree, key=lambda x: x["score"], reverse=True)
        top_thought = None
        for t in tree:
            if t["status"] != "pruned":
                top_thought = t
                break

        if not top_thought:
            return []
        return top_thought["next_questions"][:max_questions]
    
    def get_final_diagnosis(self, tree, confidence_threshold=0.7):
        if not tree:
            return None
        top_thought = tree[0]
        score = top_thought["score"]
        matched_count = len(top_thought["matched"])
        literature_supported = matched_count >= 4

    # --------------------------------------------------
    # Final stopping logic
    # --------------------------------------------------
        if score >= confidence_threshold or (score >= 0.55 and literature_supported):
            return {
                "disease": top_thought["disease"],
                "score": top_thought["score"],
                "matched_symptoms": top_thought["matched"],
                "confidence": "high" if score >= 0.8 else "medium"
            }

        return None


# ---------------------------------------------------------
# GLOBAL INSTANCE
# ---------------------------------------------------------
_tot = None


def get_tot(dataset_path="dataset.csv", severity_path="Symptom-severity.csv"):
    global _tot
    if _tot is None:
        _tot = TreeOfThoughts(dataset_path, severity_path)
    return _tot


def build_tree_of_thoughts(ranked_diseases, top_k=3, questions_per_disease=2):
    tot = get_tot()
    return tot.build_tree_of_thoughts(ranked_diseases, top_k, questions_per_disease)