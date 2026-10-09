"""
Phase 3: Rule-Based Disease Scoring
Uses medical knowledge (severity weights) to score diseases
"""

import pandas as pd
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from symptom_normalizer import get_normalizer


class RuleBasedScorer:
    """Rule-based disease scoring using severity weights"""
    
    def __init__(self, dataset_path=None, severity_path=None):
        # Handle default paths
        if dataset_path is None:
            if os.path.exists("data/dataset.csv"):
                dataset_path = "data/dataset.csv"
            elif os.path.exists("../dataset.csv"):
                dataset_path = "../dataset.csv"
            else:
                raise FileNotFoundError("Could not find dataset.csv")
        
        if severity_path is None:
            if os.path.exists("data/Symptom-severity.csv"):
                severity_path = "data/Symptom-severity.csv"
            elif os.path.exists("../Symptom-severity.csv"):
                severity_path = "../Symptom-severity.csv"
            else:
                raise FileNotFoundError("Could not find Symptom-severity.csv")
        
        self.normalizer = get_normalizer(dataset_path)
        self.df_disease = pd.read_csv(dataset_path)
        self.df_severity = pd.read_csv(severity_path)
        
        # Build disease profiles
        self._build_disease_profiles()
        
        # Build severity map
        self._build_severity_map()
        
        # Generic symptoms (less important)
        self.GENERIC_SYMPTOMS = {"HIGH_FEVER", "FATIGUE", "HEADACHE"}
    
    def _build_disease_profiles(self):
        """Build dictionary of disease -> list of canonical symptoms"""
        symptom_cols = [c for c in self.df_disease.columns if "Symptom" in c]
        
        self.disease_profiles = {}
        for _, row in self.df_disease.iterrows():
            disease = row["Disease"]
            symptoms = []
            
            for col in symptom_cols:
                if pd.notna(row[col]):
                    canon, _ = self.normalizer.normalize_symptom(row[col])
                    if canon:
                        symptoms.append(canon)
            
            # Use set to remove duplicates, then convert back to list
            if disease not in self.disease_profiles:
                self.disease_profiles[disease] = set()
            self.disease_profiles[disease].update(symptoms)
        
        # Convert sets to lists
        self.disease_profiles = {
            k: list(v) for k, v in self.disease_profiles.items()
        }
        
        print(f"Built profiles for {len(self.disease_profiles)} diseases")
    
    def _build_severity_map(self):
        """Build mapping from canonical symptom to severity weight"""
        self.severity_map = {}
        for _, row in self.df_severity.iterrows():
            canon, _ = self.normalizer.normalize_symptom(row["Symptom"])
            if canon:
                self.severity_map[canon] = row["weight"]
        
        print(f"Loaded severity weights for {len(self.severity_map)} symptoms")
    
    def score_disease(self, disease, user_symptoms):
        """
        Score a disease based on user symptoms
        
        Args:
            disease: Disease name
            user_symptoms: Set of canonical symptom names
        
        Returns:
            Tuple of (score, matched_symptoms, missing_symptoms)
        """
        if disease not in self.disease_profiles:
            return 0, [], []
        
        disease_symptoms = self.disease_profiles[disease]
        
        total_weight = 0
        matched_weight = 0
        matched = []
        missing = []
        
        for s in disease_symptoms:
            w = self.severity_map.get(s, 1)
            
            # Generic symptom penalty
            if s in self.GENERIC_SYMPTOMS:
                w *= 0.3  # Reduce weight by 70%
            
            total_weight += w
            
            if s in user_symptoms:
                matched_weight += w
                matched.append(s)
            else:
                missing.append(s)
        
        if total_weight == 0:
            return 0, [], []
        
        # Base score
        score = matched_weight / total_weight
        
        # Missing symptom penalty
        if len(matched) + len(missing) > 0:
            missing_ratio = len(missing) / (len(matched) + len(missing))
            score *= (1 - 0.3 * missing_ratio)
        
        return score, matched, missing
    
    def score_all_diseases(self, user_symptoms):
        """
        Score all diseases
        
        Args:
            user_symptoms: List of symptom strings (will be normalized)
        
        Returns:
            Dictionary mapping disease names to scores
        """
        # Normalize symptoms
        normalized = self.normalizer.normalize_symptoms(user_symptoms)
        
        disease_scores = {}
        for disease in self.disease_profiles:
            score, matched, missing = self.score_disease(disease, normalized)
            disease_scores[disease] = {
                'score': score,
                'matched': matched,
                'missing': missing
            }
        
        return disease_scores
    
    def rank_diseases(self, user_symptoms, min_score=0.1, min_matches=2):
        """
        Rank diseases by rule-based score
        
        Args:
            user_symptoms: List of symptom strings
            min_score: Minimum score to include
            min_matches: Minimum number of matched symptoms
        
        Returns:
            List of dictionaries with disease, score, matched, missing
        """
        # Normalize symptoms
        normalized = self.normalizer.normalize_symptoms(user_symptoms)
        
        # Safety check
        if len(normalized) < min_matches:
            return []
        
        results = []
        for disease in self.disease_profiles:
            score, matched, missing = self.score_disease(disease, normalized)
            
            if len(matched) < min_matches:
                continue
            
            if score >= min_score:
                results.append({
                    "disease": disease,
                    "score": round(score, 3),
                    "matched_symptoms": matched,
                    "missing_symptoms": missing
                })
        
        return sorted(results, key=lambda x: x["score"], reverse=True)


# Global instance
_scorer = None


def get_scorer(dataset_path=None, severity_path=None):
    """Get or create the global scorer instance"""
    global _scorer
    if _scorer is None:
        _scorer = RuleBasedScorer(dataset_path, severity_path)
    return _scorer


def score_disease_rule_based(disease, user_symptoms):
    """Convenience function to score a single disease"""
    scorer = get_scorer()
    return scorer.score_disease(disease, user_symptoms)


def score_all_diseases_rule_based(user_symptoms):
    """Convenience function to score all diseases"""
    scorer = get_scorer()
    return scorer.score_all_diseases(user_symptoms)

