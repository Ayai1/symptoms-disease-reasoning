import pandas as pd
import re
import json
import numpy as np
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import os


class SymptomNormalizer:
    
    def __init__(self, dataset_path=None, model_name="all-MiniLM-L6-v2"):
        # Handle default path - try current dir, then parent dir
        if dataset_path is None:
            if os.path.exists("data/dataset.csv"):
                dataset_path = "data/dataset.csv"
            elif os.path.exists("../dataset.csv"):
                dataset_path = "../dataset.csv"
            else:
                raise FileNotFoundError("Could not find dataset.csv in current or parent directory")
        
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dataset_path = dataset_path
        
        # Load data
        print("DEBUG dataset_path =", dataset_path)
        self.df_disease = pd.read_csv(dataset_path)
        
        # Build canonical symptoms
        self._build_canonical_symptoms()
        
        # Create embeddings
        self._create_embeddings()
        
        # Build symptom map
        self._build_symptom_map()
    
    def _build_canonical_symptoms(self):
    
        symptom_cols = [c for c in self.df_disease.columns if "Symptom" in c]
        
        # Extract all unique symptoms
        raw_symptoms = set()
        for col in symptom_cols:
            raw_symptoms.update(
                self.df_disease[col].dropna().astype(str).str.lower().tolist()
            )
        
        # Clean symptoms
        def clean_symptom(s):
            s = s.replace("_", " ")
            s = re.sub(r"[^a-z\s]", "", s)
            return s.strip()
        
        raw_symptoms = {clean_symptom(s) for s in raw_symptoms if clean_symptom(s)}
        
        # Expand aliases
        def expand_aliases(symptom):
            tokens = symptom.split()
            aliases = set()
            aliases.add(symptom)
            if len(tokens) > 1:
                aliases.add(" ".join(tokens[::-1]))  # Reversed
            aliases.add(symptom.replace(" pain", " ache"))
            aliases.add(symptom.replace(" ache", " pain"))
            return list(aliases)
        
        # Create canonical mappings
        self.canonical_symptoms = {}
        for symptom in raw_symptoms:
            key = symptom.upper().replace(" ", "_")
            self.canonical_symptoms[key] = expand_aliases(symptom)
        
        # Save for reference
        os.makedirs("models", exist_ok=True)
        with open("models/canonical_symptoms.json", "w") as f:
            json.dump(self.canonical_symptoms, f, indent=2)
    
    def _create_embeddings(self):
        """Create embeddings for all canonical symptoms"""
        self.canonical_keys = list(self.canonical_symptoms.keys())
        canonical_texts = [
            k.replace("_", " ").lower() + " " + " ".join(self.canonical_symptoms[k])
            for k in self.canonical_keys
        ]
        self.canonical_embeddings = self.model.encode(canonical_texts)
        print(f"Created embeddings for {len(self.canonical_keys)} canonical symptoms")
    
    def _build_symptom_map(self):
        """Build mapping from raw symptoms to canonical form"""
        symptom_cols = [c for c in self.df_disease.columns if "Symptom" in c]
        unique_symptoms = set()
        for col in symptom_cols:
            unique_symptoms.update(self.df_disease[col].dropna().astype(str))
        
        self.symptom_map = {}
        for s in unique_symptoms:
            canon, _ = self.normalize_symptom(s)
            if canon:
                self.symptom_map[s] = canon
    
    def clean_symptom(self, s):
        """Clean a symptom string"""
        s = str(s).replace("_", " ")
        s = re.sub(r"[^a-z\s]", "", s.lower())
        return s.strip()
    
    @lru_cache(maxsize=5000)
    def normalize_symptom(self, symptom, threshold=0.45):
        """
        Normalize a symptom to canonical form
        
        Args:
            symptom: Raw symptom string
            threshold: Minimum similarity threshold (default: 0.45)
        
        Returns:
            Tuple of (canonical_name, similarity_score) or (None, None)
        """
        symptom = self.clean_symptom(symptom)
        if not symptom:
            return None, None
        
        # Check if already in map
        if symptom in self.symptom_map:
            return self.symptom_map[symptom], 1.0
        
        # Use semantic matching
        emb = self.model.encode([symptom])
        sims = cosine_similarity(emb, self.canonical_embeddings)[0]
        idx = np.argmax(sims)
        
        if sims[idx] >= threshold:
            return self.canonical_keys[idx], float(sims[idx])
        return None, None
    
    def normalize_symptoms(self, symptom_list):
        """
        Normalize a list of symptoms
        
        Args:
            symptom_list: List of symptom strings
        
        Returns:
            Set of canonical symptom names
        """
        normalized = set()
        for symptom in symptom_list:
            canon, _ = self.normalize_symptom(symptom)
            if canon:
                normalized.add(canon)
        return normalized


# Global instance (will be initialized when needed)
_normalizer = None


def get_normalizer(dataset_path=None):
    """Get or create the global normalizer instance"""
    global _normalizer
    if _normalizer is None:
        _normalizer = SymptomNormalizer(dataset_path)
    return _normalizer


def normalize_symptom(symptom, threshold=0.45):
    """Convenience function to normalize a single symptom"""
    normalizer = get_normalizer()
    return normalizer.normalize_symptom(symptom, threshold)


def normalize_symptoms(symptom_list):
    """Convenience function to normalize a list of symptoms"""
    normalizer = get_normalizer()
    return normalizer.normalize_symptoms(symptom_list)

