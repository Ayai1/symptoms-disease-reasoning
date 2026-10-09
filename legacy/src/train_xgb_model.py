import pandas as pd
import numpy as np
import pickle
import os
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from symptom_normalizer import get_normalizer


def prepare_data(dataset_path=None):
    if dataset_path is None:
        if os.path.exists("dataset.csv"):
            dataset_path = "dataset.csv"
        else:
            dataset_path = "../dataset.csv"

    df = pd.read_csv(dataset_path)
    symptom_cols = [c for c in df.columns if "Symptom" in c]

    normalizer = get_normalizer(dataset_path)

    # collect canonical symptoms
    all_symptoms = set()
    for _, row in df.iterrows():
        for col in symptom_cols:
            if pd.notna(row[col]):
                canon, _ = normalizer.normalize_symptom(row[col])
                if canon:
                    all_symptoms.add(canon)

    symptom_names = sorted(list(all_symptoms))
    symptom_to_idx = {s:i for i,s in enumerate(symptom_names)}

    X = []
    y = []

    for _, row in df.iterrows():
        vec = [0]*len(symptom_names)
        for col in symptom_cols:
            if pd.notna(row[col]):
                canon,_ = normalizer.normalize_symptom(row[col])
                if canon in symptom_to_idx:
                    vec[symptom_to_idx[canon]] = 1
        if sum(vec)>0:
            X.append(vec)
            y.append(row["Disease"])

    X = np.array(X)
    y = np.array(y)

    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    return X, y_enc, symptom_names, le


def train_xgb_model(save_path="models/xgb_model.pkl"):
    print("\nTraining XGBoost Prior Model")

    X,y,symptom_names,label_encoder = prepare_data()

    X_train,X_test,y_train,y_test = train_test_split(
        X,y,test_size=0.2,random_state=42,stratify=y
    )

    model = XGBClassifier(
        objective="multi:softprob",
        num_class=len(label_encoder.classes_),
        max_depth=4,
        learning_rate=0.05,
        n_estimators=250,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="mlogloss",
        n_jobs=-1
    )

    model.fit(X_train,y_train)

    os.makedirs("models",exist_ok=True)

    with open(save_path,"wb") as f:
        pickle.dump({
            "model":model,
            "label_encoder":label_encoder,
            "symptom_names":symptom_names
        },f)

    print("XGBoost model saved:",save_path)


if __name__=="__main__":
    train_xgb_model()