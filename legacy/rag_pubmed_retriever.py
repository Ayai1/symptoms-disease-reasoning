from rag_pubmed_loader import iter_pubmed_abstracts
from rag_pubmed_index import build_pubmed_index

def search_pubmed(query_terms, max_docs=5):
    """
    MeSH-aware PubMed retrieval.
    First term in query_terms is assumed to be the disease.
    """

    results = []

    # ⭐ First term = disease anchor
    disease_term = query_terms[0].lower()
    symptom_terms = [q.lower() for q in query_terms[1:]]

    docs = build_pubmed_index(max_files=3)
    for doc in docs:

        title = doc["title"].lower()
        abstract = doc["abstract"].lower()
        mesh = doc.get("mesh_terms", [])
        mesh_text = " ".join(mesh)
        disease_words = disease_term.split()

        if not any(dw in mesh_text for dw in disease_words):
         continue

        # ------------------------------------------------
        # SCORE DOCUMENT
        # ------------------------------------------------
        score = 0

        # strong disease matches
        if disease_term in title:
            score += 4
        if disease_term in abstract:
            score += 2

        # weaker symptom matches
        for s in symptom_terms:
            if s in title:
                score += 1
            if s in abstract:
                score += 1

        if score > 0 and len(abstract) > 200:
            results.append((score, doc))

    results.sort(key=lambda x: x[0], reverse=True)

    return [d for _, d in results[:max_docs]]