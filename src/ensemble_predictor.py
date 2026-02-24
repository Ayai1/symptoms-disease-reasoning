"""
Phase 4: Ensemble Predictor
Combines Random Forest (data-driven) and Rule-Based (knowledge-driven) predictions
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from xgb_predictor import get_predictor
from rule_based_scorer import get_scorer
from symptom_normalizer import normalize_symptoms


class EnsemblePredictor:
    """Combines RF and rule-based predictions"""
    
    def __init__(self, rf_model_path="models/rf_model.pkl", 
                 dataset_path="dataset.csv",
                 severity_path="Symptom-severity.csv",
                 alpha=0.4, beta=0.6):
        """
        Initialize ensemble predictor
        
        Args:
            rf_model_path: Path to trained RF model
            dataset_path: Path to dataset.csv
            severity_path: Path to Symptom-severity.csv
            alpha: Weight for RF predictions (default: 0.4)
            beta: Weight for rule-based scores (default: 0.6)
        """
        self.alpha = alpha
        self.beta = beta
        self.rf_predictor = get_predictor(rf_model_path)
        self.rule_scorer = get_scorer(dataset_path, severity_path)
        
        print(f"Ensemble predictor initialized (RF: {alpha}, Rule-based: {beta})")
    
    def predict(self, user_symptoms, min_score=0.1, min_matches=2):
        """
        Get ensemble predictions
        
        Args:
            user_symptoms: List of symptom strings
            min_score: Minimum final score to include
            min_matches: Minimum symptom matches
        
        Returns:
            List of dictionaries with disease, score, matched, missing, rf_prob, rule_score
        """
        # Normalize symptoms
        normalized = normalize_symptoms(user_symptoms)
        
        if len(normalized) < min_matches:
            return []
        
        # Get RF probabilities
        rf_probs = self.rf_predictor.predict(user_symptoms)
        
        # Get rule-based scores
        rule_scores = self.rule_scorer.score_all_diseases(user_symptoms)
        
        # Combine predictions
        results = []
        
        # Get all unique diseases
        all_diseases = set(rf_probs.keys()) | set(rule_scores.keys())
        
        for disease in all_diseases:
            # Get RF probability (default to 0 if not in RF predictions)
            rf_prob = rf_probs.get(disease, 0.0)
            
            # Get rule-based score and details
            rule_data = rule_scores.get(disease, {'score': 0.0, 'matched': [], 'missing': []})
            rule_score = rule_data['score']
            matched = rule_data['matched']
            missing = rule_data['missing']
            
            # Skip if not enough matches
            if len(matched) < min_matches:
                continue
            
            # Ensemble combination
            # Normalize both to 0-1 range (they should already be, but ensure)
            rf_prob = max(0.0, min(1.0, rf_prob))
            rule_score = max(0.0, min(1.0, rule_score))
            
            final_score = rule_score * (1 + self.alpha * rf_prob)
            final_score = min(final_score, 1.0)

            
            if final_score >= min_score:
                results.append({
                    "disease": disease,
                    "confidence": round(final_score, 3),
                    "prior_support": round(rf_prob, 3),
                    "evidence_score": round(rule_score, 3),
                    "matched_symptoms": matched,
                    "missing_symptoms": missing
                })
        
        # Sort by final score
        return sorted(results, key=lambda x: x["confidence"], reverse=True)
    
    def predict_top_k(self, user_symptoms, k=5, min_score=0.1, min_matches=2):
        """
        Get top K ensemble predictions
        
        Args:
            user_symptoms: List of symptom strings
            k: Number of top predictions
            min_score: Minimum final score
            min_matches: Minimum symptom matches
        
        Returns:
            Top K predictions
        """
        predictions = self.predict(user_symptoms, min_score, min_matches)
        return predictions[:k]


# Global instance
_ensemble = None


def get_ensemble(alpha=0.4, beta=0.6, rf_model_path="models/rf_model.pkl",
                 dataset_path="dataset.csv", severity_path="Symptom-severity.csv"):
    """Get or create the global ensemble instance"""
    global _ensemble
    if _ensemble is None or _ensemble.alpha != alpha or _ensemble.beta != beta:
        _ensemble = EnsemblePredictor(rf_model_path, dataset_path, severity_path, alpha, beta)
    return _ensemble


def ensemble_predict(user_symptoms, alpha=0.4, beta=0.6, min_score=0.1, min_matches=2):
    """
    Convenience function for ensemble prediction
    
    Args:
        user_symptoms: List of symptom strings
        alpha: RF weight
        beta: Rule-based weight
        min_score: Minimum score
        min_matches: Minimum matches
    
    Returns:
        Ranked list of predictions
    """
    ensemble = get_ensemble(alpha, beta)
    return ensemble.predict(user_symptoms, min_score, min_matches)

