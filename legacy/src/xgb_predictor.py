import pickle
import numpy as np
import os
from symptom_normalizer import normalize_symptoms


class XGBPredictor:

    def __init__(self,model_path="models/xgb_model.pkl"):
        with open(model_path,"rb") as f:
            data = pickle.load(f)

        self.model = data["model"]
        self.label_encoder = data["label_encoder"]
        self.symptom_names = data["symptom_names"]
        self.symptom_to_idx = {s:i for i,s in enumerate(self.symptom_names)}

        print(f"Loaded XGB model with {len(self.symptom_names)} symptoms")

    def predict(self,user_symptoms):
        normalized = normalize_symptoms(user_symptoms)

        vec = np.zeros(len(self.symptom_names))
        for s in normalized:
            if s in self.symptom_to_idx:
                vec[self.symptom_to_idx[s]] = 1

        if vec.sum()==0:
            return {}

        probs = self.model.predict_proba([vec])[0]

        # soften probabilities slightly
        probs = probs**0.8
        probs = probs/probs.sum()

        out = {}
        for idx,p in enumerate(probs):
            disease = self.label_encoder.inverse_transform([idx])[0]
            out[disease] = float(p)

        return dict(sorted(out.items(),key=lambda x:x[1],reverse=True))


_predictor=None

def get_predictor(model_path="models/xgb_model.pkl"):
    global _predictor
    if _predictor is None:
        _predictor = XGBPredictor(model_path)
    return _predictor