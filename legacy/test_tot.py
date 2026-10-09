from main_pipeline import diagnose
from tree_of_thoughts import get_tot

# --------------------------------------------------
# STEP 1 — Run diagnosis normally
# --------------------------------------------------
result = diagnose(["fever", "cough", "breathing difficulty"])

print("\n=== INITIAL DIAGNOSIS ===")
for d in result["diagnoses"]:
    print(d["disease"], d["confidence"])

# --------------------------------------------------
# STEP 2 — Inspect Tree of Thoughts
# --------------------------------------------------
tree = result["tree"]

print("\n=== TREE OF THOUGHTS ===")
for node in tree:
    print("\nDisease:", node["disease"])
    print("Score:", node["score"])
    print("Next questions:")
    for q in node["next_questions"]:
        print("  -", q["question"])

print("\n=== LITERATURE SUPPORT ===")
for ev in result["diagnoses"][0]["literature_support"]:
    print("-", ev["title"])
# --------------------------------------------------
# STEP 3 — Simulate answering questions
# --------------------------------------------------
# --------------------------------------------------
# STEP 3 — Interactive questioning (UPDATED)
# --------------------------------------------------
tot = get_tot()

while True:
    questions = tot.get_next_questions(tree)

    if not questions:
        break

    answers = {}

    for q in questions:
        ans = input(q["question"] + " (yes/no): ")
        answers[q["symptom"]] = ans

    tree = tot.update_tree_with_answers(tree, answers)

    final = tot.get_final_diagnosis(tree)
    if final:
        print("\nFINAL:", final)
        break
# --------------------------------------------------
# STEP 4 — Check final diagnosis
# --------------------------------------------------
final = tot.get_final_diagnosis(tree)

print("\n=== FINAL RESULT ===")
print(final)