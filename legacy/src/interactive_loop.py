"""
Phase 6: Interactive Diagnosis Loop
Handles user interaction for iterative diagnosis refinement
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from main_pipeline import diagnose, get_diagnosis_summary
from tree_of_thoughts import get_tot


def interactive_diagnosis(initial_symptoms, max_iterations=5, 
                         confidence_threshold=0.7, alpha=0.4, beta=0.6):
    """
    Interactive diagnosis loop with Q&A
    
    Args:
        initial_symptoms: List of initial symptom strings
        max_iterations: Maximum number of Q&A rounds
        confidence_threshold: Score threshold to stop early
        alpha: RF weight
        beta: Rule-based weight
    
    Returns:
        Final diagnosis result
    """
    print("\n" + "=" * 80)
    print("INTERACTIVE MEDICAL DIAGNOSIS SYSTEM")
    print("=" * 80)
    print(f"\nInitial symptoms: {', '.join(initial_symptoms)}")
    print("\nStarting diagnosis...\n")
    
    current_symptoms = initial_symptoms.copy()
    tot = get_tot()
    
    for iteration in range(max_iterations):
        # Get diagnosis
        result = diagnose(current_symptoms, alpha=alpha, beta=beta)
        
        # Check if we have high confidence
        if result['confidence'] == "high" and iteration >= 1:
            print("\n" + "=" * 80)
            print("HIGH CONFIDENCE DIAGNOSIS REACHED")
            print("=" * 80)
            print(get_diagnosis_summary(result))
            return result
        
        # Display current results
        print(f"\n--- Iteration {iteration + 1} ---")
        print(f"Top 3 Hypotheses:")
        for i, diag in enumerate(result['diagnoses'][:3], 1):
            print(f"  {i}. {diag['disease']}: {diag['confidence']:.1%}")
        
        # Get questions from tree
        questions = tot.get_next_questions(result['tree'], max_questions=3)
        
        if not questions:
            print("\nNo more questions available.")
            break
        
        # Ask questions
        print(f"\nFollow-up Questions (Round {iteration + 1}):")
        answers = {}
        
        for q in questions:
            while True:
                answer = input(f"  {q['question']} (yes/no/skip): ").strip().lower()
                if answer in ['yes', 'y', 'no', 'n', 'skip', 's', '']:
                    if answer in ['skip', 's', '']:
                        break
                    answers[q['symptom']] = answer
                    break
                else:
                    print("    Please answer 'yes', 'no', or 'skip'")
        
        if not answers:
            print("\nNo answers provided. Ending diagnosis.")
            break
        
        # Update symptoms based on answers
        for symptom, answer in answers.items():
            if answer in ['yes', 'y']:
                # Add symptom to current list (will be normalized in next iteration)
                symptom_readable = symptom.replace("_", " ").lower()
                if symptom_readable not in [s.lower() for s in current_symptoms]:
                    current_symptoms.append(symptom_readable)
        
        # Update tree with answers
        result['tree'] = tot.update_tree_with_answers(result['tree'], answers)
        
        # Check for final diagnosis
        final = tot.get_final_diagnosis(result['tree'], confidence_threshold)
        if final:
            print("\n" + "=" * 80)
            print("FINAL DIAGNOSIS")
            print("=" * 80)
            print(f"\nMost Likely: {final['disease']} ({final['score']:.1%} confidence)")
            print(f"Matched Symptoms: {', '.join(final['matched_symptoms'])}")
            return result
    
    # Final results after max iterations
    print("\n" + "=" * 80)
    print("FINAL RESULTS (After Maximum Iterations)")
    print("=" * 80)
    print(get_diagnosis_summary(result))
    
    return result


def simple_diagnosis(symptoms, alpha=0.4, beta=0.6, top_k=5):
    """
    Simple one-shot diagnosis without interaction
    
    Args:
        symptoms: List of symptom strings
        alpha: RF weight
        beta: Rule-based weight
        top_k: Number of top diagnoses
    
    Returns:
        Diagnosis result
    """
    result = diagnose(symptoms, alpha=alpha, beta=beta, top_k=top_k)
    print(get_diagnosis_summary(result))
    return result


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        # Command line usage
        symptoms = sys.argv[1:]
        print(f"Diagnosing: {', '.join(symptoms)}\n")
        simple_diagnosis(symptoms)
    else:
        # Interactive mode
        print("Enter your symptoms (comma-separated):")
        user_input = input("> ").strip()
        symptoms = [s.strip() for s in user_input.split(",") if s.strip()]
        
        if symptoms:
            use_interactive = input("\nUse interactive mode? (yes/no): ").strip().lower()
            if use_interactive in ['yes', 'y']:
                interactive_diagnosis(symptoms)
            else:
                simple_diagnosis(symptoms)
        else:
            print("No symptoms provided.")

