"""
Quick script to train the Random Forest model
Run this before using the diagnostic system
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from train_rf_model import train_random_forest

if __name__ == "__main__":
    print("Training Random Forest Model...")
    print("This may take a few minutes...\n")
    
    try:
        train_random_forest()
        print("\n✅ Training completed successfully!")
        print("You can now use the diagnostic system.")
    except Exception as e:
        print(f"\n❌ Error during training: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

