from main_pipeline import diagnose
from rag_pubmed_retriever import search_pubmed
from rag_rxnorm_loader import load_rxnorm_drug_names

def build_rag_query(diagnosis_result):
    """
    Build internal search terms from structured reasoning.
    Users never see this.
    """

    if not diagnosis_result["diagnoses"]:
        return []

    top = diagnosis_result["diagnoses"][0]

    disease = top["disease"].lower()
    symptoms = [
        s.replace("_", " ").lower()
        for s in top.get("matched_symptoms", [])
    ]

    return [disease] + symptoms

import re

EXCLUDE_TERMS = {"placebo","virus","control","study"}
EXCLUDE_PARTIAL = {"vaccine","influenza"}

def extract_rxnorm_drugs(text, drug_set, max_hits=5):

    text = text.lower()
    sorted_drugs = sorted(drug_set, key=len, reverse=True)

    hits = []

    for d in sorted_drugs:

        if d in EXCLUDE_TERMS:
            continue

        if any(x in d for x in EXCLUDE_PARTIAL):
            continue

        pattern = r"\b" + re.escape(d) + r"\b"

        if re.search(pattern, text):

            if any(d in h for h in hits):
                continue

            hits.append(d)

        if len(hits) >= max_hits:
            break

    return hits



def rag_explain(symptoms, max_docs=3):

    result = diagnose(symptoms)

    query_terms = build_rag_query(result)

    pubmed_docs = search_pubmed(query_terms, max_docs=max_docs)

    # load rxnorm drug names ONCE
    drug_set = load_rxnorm_drug_names()

    explanations = []

    for doc in pubmed_docs:

        drugs_found = extract_rxnorm_drugs(
            doc["abstract"],
            drug_set
        )

        explanations.append({
            "title": doc["title"],
            "summary": doc["abstract"][:400] + "...",
            "rxnorm_drugs": drugs_found
        })

    result["rag_explanations"] = explanations

    return result