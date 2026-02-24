from pathlib import Path

RXNORM_DIR = Path("rag_data/rxnorm")

VALID_TTY = {"IN", "SCD", "SBD"}

def load_rxnorm_drug_names(limit=120000):

    file = RXNORM_DIR / "RXNCONSO.RRF"

    drugs = set()

    with open(file, encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):

            parts = line.split("|")

            if len(parts) > 14:

                tty = parts[12]        # ⭐ term type
                name = parts[14].lower().strip()

                if tty not in VALID_TTY:
                    continue

                if len(name) < 6:
                    continue

                if not any(c.isalpha() for c in name):
                    continue

                drugs.add(name)

            if i > limit:
                break

    return drugs