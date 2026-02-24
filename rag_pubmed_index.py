from rag_pubmed_loader import iter_pubmed_abstracts

# global cache
PUBMED_INDEX = None


def build_pubmed_index(max_files=3):
    """
    Loads PubMed abstracts into memory once.
    """

    global PUBMED_INDEX

    if PUBMED_INDEX is not None:
        return PUBMED_INDEX

    print("Building PubMed in-memory index...")

    PUBMED_INDEX = list(iter_pubmed_abstracts(max_files=max_files))

    print("Indexed documents:", len(PUBMED_INDEX))

    return PUBMED_INDEX