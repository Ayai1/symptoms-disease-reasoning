from lxml import etree
from pathlib import Path

# Folder containing your extracted PubMed XML files
PUBMED_DIR = Path("rag_data/pubmed")


def iter_pubmed_abstracts(max_files=5):
    """
    Streams PubMed abstracts from local XML files.

    Returns dictionaries:
    {
        "title": str,
        "abstract": str,
        "mesh_terms": list[str]
    }

    Uses streaming parsing so large files don't fill RAM.
    """

    # ⭐ since your files are already extracted (.xml)
    files = sorted(PUBMED_DIR.glob("*.xml"))[:max_files]

    for file in files:
        print("Reading:", file.name)

        with open(file, "rb") as f:

            # iterate article-by-article
            context = etree.iterparse(
                f,
                events=("end",),
                tag="PubmedArticle"
            )

            for _, elem in context:

                try:
                    # -----------------------------
                    # TITLE
                    # -----------------------------
                    title_elem = elem.find(".//ArticleTitle")
                    title = (
                        "".join(title_elem.itertext())
                        if title_elem is not None
                        else None
                    )

                    # -----------------------------
                    # ABSTRACT (can have many sections)
                    # -----------------------------
                    abstract_parts = elem.findall(".//AbstractText")

                    abstract = (
                        " ".join(
                            "".join(a.itertext())
                            for a in abstract_parts
                        )
                        if abstract_parts
                        else None
                    )

                    # -----------------------------
                    # MeSH TERMS (disease metadata)
                    # -----------------------------
                    mesh_terms = [
                        m.text.lower()
                        for m in elem.findall(".//MeshHeading/DescriptorName")
                        if m.text
                    ]

                    # -----------------------------
                    # YIELD CLEAN RESULT
                    # -----------------------------
                    if title and abstract:

                        yield {
                            "title": title.strip(),
                            "abstract": abstract.strip(),
                            "mesh_terms": mesh_terms
                        }

                except Exception:
                    # Skip malformed entries silently
                    pass

                # ⭐ VERY IMPORTANT:
                # clear XML element to avoid RAM growth
                elem.clear()