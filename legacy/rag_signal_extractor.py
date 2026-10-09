import re
from rag_pubmed_retriever import search_pubmed


def extract_rag_keywords(query_terms, max_docs=3):
    """
    Pulls high-signal clinical keywords from retrieved PubMed abstracts.
    Lightweight — no embeddings needed.
    """

    docs = search_pubmed(query_terms, max_docs=max_docs)

    word_freq = {}

    for doc in docs:
        text = doc["abstract"].lower()

        words = re.findall(r"\b[a-z][a-z\-]+\b", text)

        for w in words:

            # ignore generic words
            if len(w) < 5:
                continue

            if w in {"study","patients","disease","clinical","effect"}:
                continue

            word_freq[w] = word_freq.get(w, 0) + 1

    # return top keywords
    ranked = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

    return [w for w,_ in ranked[:15]]