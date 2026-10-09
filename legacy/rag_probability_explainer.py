from rag_pubmed_retriever import search_pubmed


def build_probability_explanation(disease, matched_symptoms):
    """
    Build literature-based explanation for WHY a disease score is high.
    """

    query_terms = [disease.lower()] + [
        s.replace("_", " ").lower()
        for s in matched_symptoms
    ]

    docs = search_pubmed(query_terms, max_docs=3)

    evidence = []

    for d in docs:
        evidence.append({
            "title": d["title"],
            "snippet": d["abstract"][:200] + "..."
        })

    return evidence