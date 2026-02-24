from rag_explainer import rag_explain

res = rag_explain(["fever","cough","breathing difficulty"])

for e in res["rag_explanations"]:
    print("\nTITLE:", e["title"])
    print("DRUGS:", e["rxnorm_drugs"])