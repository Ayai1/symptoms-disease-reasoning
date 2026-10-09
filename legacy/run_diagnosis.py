"""
Quick script to run diagnosis
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from interactive_loop import simple_diagnosis, interactive_diagnosis

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_diagnosis.py <symptom1> <symptom2> ...")
        print("Example: python run_diagnosis.py 'high fever' 'cough' 'chest pain'")
        sys.exit(1)
    
    symptoms = sys.argv[1:]
    print(f"\nDiagnosing symptoms: {', '.join(symptoms)}\n")
    
    # Check if model exists
    if not os.path.exists("models/rf_model.pkl"):
        print("❌ Error: Random Forest model not found!")
        print("Please run 'python run_training.py' first to train the model.")
        sys.exit(1)
    
    # Ask for interactive mode
    use_interactive = input("Use interactive mode? (yes/no, default: no): ").strip().lower()
    
    if use_interactive in ['yes', 'y']:
        interactive_diagnosis(symptoms)
    else:
        simple_diagnosis(symptoms)

