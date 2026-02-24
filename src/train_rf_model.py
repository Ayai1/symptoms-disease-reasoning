"""
Phase 2: Train Random Forest Model on dataset.csv
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import pickle
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from symptom_normalizer import get_normalizer


def prepare_data(dataset_path=None):
    """
    Transform dataset.csv into binary feature matrix for Random Forest
    
    Args:
        dataset_path: Path to dataset.csv (default: looks in current dir or parent)
    
    Returns:
        X: Binary feature matrix (n_samples, n_symptoms)
        y: Disease labels
        symptom_names: List of symptom names (columns)
        label_encoder: LabelEncoder for diseases
    """
    # Handle default path - try current dir, then parent dir
    if dataset_path is None:
        if os.path.exists("dataset.csv"):
            dataset_path = "dataset.csv"
        elif os.path.exists("../dataset.csv"):
            dataset_path = "../dataset.csv"
        else:
            raise FileNotFoundError("Could not find dataset.csv in current or parent directory")
    
    print("Loading dataset...")
    df = pd.read_csv(dataset_path)
    
    # Get symptom columns
    symptom_cols = [c for c in df.columns if "Symptom" in c]
    
    # Normalize symptoms
    normalizer = get_normalizer(dataset_path)
    
    # Collect all unique symptoms (canonical)
    all_symptoms = set()
    for _, row in df.iterrows():
        for col in symptom_cols:
            if pd.notna(row[col]):
                canon, _ = normalizer.normalize_symptom(row[col])
                if canon:
                    all_symptoms.add(canon)
    
    symptom_names = sorted(list(all_symptoms))
    print(f"Found {len(symptom_names)} unique symptoms")
    
    # Create binary feature matrix
    X = []
    y = []
    
    for _, row in df.iterrows():
        disease = row["Disease"]
        symptom_vector = [0] * len(symptom_names)
        
        for col in symptom_cols:
            if pd.notna(row[col]):
                canon, _ = normalizer.normalize_symptom(row[col])
                if canon and canon in symptom_names:
                    idx = symptom_names.index(canon)
                    symptom_vector[idx] = 1
        
        # Only add if at least one symptom is present
        if sum(symptom_vector) > 0:
            X.append(symptom_vector)
            y.append(disease)
    
    X = np.array(X)
    y = np.array(y)
    
    print(f"Created feature matrix: {X.shape}")
    print(f"Number of diseases: {len(set(y))}")
    
    # Encode disease labels
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    
    return X, y_encoded, symptom_names, label_encoder


def train_random_forest(dataset_path=None, 
                        n_estimators=150,
                        test_size=0.2,
                        random_state=42,
                        save_path="models/rf_model.pkl"):
    """
    Train Random Forest classifier
    
    Args:
        dataset_path: Path to dataset.csv
        n_estimators: Number of trees
        test_size: Test set size
        random_state: Random seed
        save_path: Where to save the model
    
    Returns:
        Trained model, label_encoder, symptom_names
    """
    print("\n" + "="*60)
    print("Training Random Forest Model")
    print("="*60)
    
    # Handle default path
    if dataset_path is None:
        if os.path.exists("dataset.csv"):
            dataset_path = "dataset.csv"
        elif os.path.exists("../dataset.csv"):
            dataset_path = "../dataset.csv"
        else:
            raise FileNotFoundError("Could not find dataset.csv in current or parent directory")
    
    # Prepare data
    X, y, symptom_names, label_encoder = prepare_data(dataset_path)
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    print(f"\nTrain set: {X_train.shape[0]} samples")
    print(f"Test set: {X_test.shape[0]} samples")
    
    # Train model
    print("\nTraining Random Forest...")
    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=None,
        random_state=random_state,
        n_jobs=-1,
        class_weight='balanced'
    )

    clf.fit(X_train, y_train)
    
    # Evaluate
    
    print(f"\n{'='*60}")
    print("RF internal sanity check accuracy (not diagnostic performance)")
    print(f"{'='*60}")
    
    # Save model
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    model_data = {
        'model': clf,
        'label_encoder': label_encoder,
        'symptom_names': symptom_names
    }
    
    with open(save_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    print(f"\nModel saved to: {save_path}")
    
    # Print classification report



if __name__ == "__main__":
    # Train the model
    train_random_forest()

# NOTE:
# RF is used only as a prior estimator,not a final diagnostic classifier.
# Traditional accuracy/F1 metrics are not meaningful for this task