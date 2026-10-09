from __future__ import annotations

from app.safety.text import NegationDetector, Normalizer


def test_normalizer_restores_contractions_and_spelling() -> None:
    norm = Normalizer({"cant": "can't", "im": "i'm"}, {"chset": "chest"})
    assert norm.normalize("Im  OK but CANT feel my CHSET") == "i'm ok but can't feel my chest"


def test_normalizer_straightens_apostrophes_and_nfkc() -> None:
    norm = Normalizer({}, {})
    curly_apostrophe, fullwidth_bang = chr(0x2019), chr(0xFF01)
    text = f"I can{curly_apostrophe}t   breathe{fullwidth_bang}"
    assert norm.normalize(text) == "i can't breathe!"


def test_normalizer_only_replaces_whole_words() -> None:
    norm = Normalizer({"im": "i'm"}, {})
    assert norm.normalize("immune") == "immune"


def _detector() -> NegationDetector:
    return NegationDetector(
        triggers=["no", "not", "don't have"],
        pseudo_triggers=["not sure"],
        terminators=["but"],
        window_tokens=6,
    )


def test_negation_in_same_clause() -> None:
    text = "i don't have chest pain"
    assert _detector().is_negated(text, text.index("chest"))


def test_negation_stops_at_terminator_word() -> None:
    text = "no fever but chest pain"
    assert not _detector().is_negated(text, text.index("chest"))


def test_negation_stops_at_punctuation() -> None:
    text = "no fever, chest pain"
    assert not _detector().is_negated(text, text.index("chest"))


def test_pseudo_trigger_does_not_negate() -> None:
    text = "not sure if it is chest pain"
    assert not _detector().is_negated(text, text.index("chest"))


def test_negation_window_is_limited() -> None:
    text = "no one in my family ever told me about this chest pain"
    assert not _detector().is_negated(text, text.index("chest"))
