"""
Phase 2: Random Forest Predictor
Loads trained model and makes predictions
"""

import pickle
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from symptom_normalizer import normalize_symptoms


class RFPredictor:
    """Random Forest predictor for diseases"""
    
    def __init__(self, model_path="models/rf_model.pkl"):
        """
        Load trained Random Forest model
        
        Args:
            model_path: Path to saved model
        """
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.label_encoder = model_data['label_encoder']
        self.symptom_names = model_data['symptom_names']
        
        # Create symptom index map for fast lookup
        self.symptom_to_idx = {symptom: idx for idx, symptom in enumerate(self.symptom_names)}
        
        print(f"Loaded RF model with {len(self.symptom_names)} symptoms and "
              f"{len(self.label_encoder.classes_)} diseases")
    
    def predict(self, user_symptoms):
        """
        Predict disease probabilities for given symptoms
        
        Args:
            user_symptoms: List of symptom strings (will be normalized)
        
        Returns:
            Dictionary mapping disease names to probabilities
        """
        # Normalize symptoms
        normalized = normalize_symptoms(user_symptoms)
        
        # Create binary feature vector
        feature_vector = np.zeros(len(self.symptom_names))
        for symptom in normalized:
            if symptom in self.symptom_to_idx:
                idx = self.symptom_to_idx[symptom]
                feature_vector[idx] = 1
        
        # If no symptoms matched, return empty dict
        if feature_vector.sum() == 0:
            return {}
        
        # Get probabilities
        probs = self.model.predict_proba([feature_vector])[0]
        probs = probs ** 0.7
        probs = probs / probs.sum()

        # Create dictionary
        disease_probs = {}
        for idx, prob in enumerate(probs):
            disease_name = self.label_encoder.inverse_transform([idx])[0]
            disease_probs[disease_name] = float(prob)
        
        # Sort by probability
        return dict(sorted(disease_probs.items(), key=lambda x: x[1], reverse=True))
    
    def predict_top_k(self, user_symptoms, k=5):
        """
        Get top K disease predictions
        
        Args:
            user_symptoms: List of symptom strings
            k: Number of top predictions to return
        
        Returns:
            List of tuples (disease, probability) sorted by probability
        """
        probs = self.predict(user_symptoms)
        return list(probs.items())[:k]


# Global instance
_predictor = None


def get_predictor(model_path="models/rf_model.pkl"):
    """Get or create the global predictor instance"""
    global _predictor
    if _predictor is None:
        _predictor = RFPredictor(model_path)
    return _predictor


def predict_rf(user_symptoms, model_path="models/rf_model.pkl"):
    """Convenience function to get RF predictions"""
    predictor = get_predictor(model_path)
    return predictor.predict(user_symptoms)

