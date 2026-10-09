"""Text normalization and clause-scoped negation for safety matching."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence

# Right/left single quotes, backtick and acute accent -> straight apostrophe.
_APOSTROPHES = str.maketrans({0x2019: "'", 0x2018: "'", 0x60: "'", 0xB4: "'"})
_WHITESPACE = re.compile(r"\s+")
_CLAUSE_PUNCTUATION = re.compile(r"[.;:!?,\n]")
_TOKEN = re.compile(r"[a-z0-9']+")


def _word_replacer(words: Mapping[str, str]) -> re.Pattern[str] | None:
    if not words:
        return None
    alternation = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    return re.compile(rf"(?<![a-z0-9'])({alternation})(?![a-z0-9'])")


def _phrase_pattern(phrases: Sequence[str]) -> re.Pattern[str] | None:
    if not phrases:
        return None
    alternation = "|".join(
        re.escape(p).replace(r"\ ", r"\s+") for p in sorted(phrases, key=len, reverse=True)
    )
    return re.compile(rf"(?<![a-z0-9'])({alternation})(?![a-z0-9'])")


def _lookup(table: dict[str, str]) -> Callable[[re.Match[str]], str]:
    def replace(match: re.Match[str]) -> str:
        return table[match.group(1)]

    return replace


class Normalizer:
    """Lowercase, NFKC, straight apostrophes, collapsed whitespace, and word fixes.

    Word fixes restore apostrophe-less contractions ("cant" -> "can't") and
    correct common misspellings of safety-relevant words.
    """

    def __init__(self, contractions: Mapping[str, str], spelling: Mapping[str, str]) -> None:
        self._maps: list[tuple[re.Pattern[str], dict[str, str]]] = []
        for mapping in (contractions, spelling):
            pattern = _word_replacer(mapping)
            if pattern is not None:
                self._maps.append((pattern, dict(mapping)))

    def normalize(self, text: str) -> str:
        out = unicodedata.normalize("NFKC", text).translate(_APOSTROPHES).lower()
        out = _WHITESPACE.sub(" ", out).strip()
        for pattern, mapping in self._maps:
            out = pattern.sub(_lookup(mapping), out)
        return out


class NegationDetector:
    """NegEx-style check: is a match negated earlier in the same clause?

    The clause runs from the last boundary (punctuation or a terminator word
    such as "but") to the start of the match. Only the last ``window_tokens``
    tokens of that clause are considered. Pseudo-triggers ("not sure") are
    removed before looking for triggers ("not").
    """

    def __init__(
        self,
        triggers: Sequence[str],
        pseudo_triggers: Sequence[str],
        terminators: Sequence[str],
        window_tokens: int = 6,
    ) -> None:
        self._trigger_re = _phrase_pattern(triggers)
        self._pseudo_re = _phrase_pattern(pseudo_triggers)
        self._terminator_re = _phrase_pattern(terminators)
        self.window_tokens = window_tokens

    def clause_window(self, text: str, start: int) -> str:
        prefix = text[:start]
        cut = 0
        for match in _CLAUSE_PUNCTUATION.finditer(prefix):
            cut = max(cut, match.end())
        if self._terminator_re is not None:
            for match in self._terminator_re.finditer(prefix):
                cut = max(cut, match.end())
        tokens = _TOKEN.findall(prefix[cut:])
        return " ".join(tokens[-self.window_tokens :])

    def is_negated(self, text: str, start: int) -> bool:
        if self._trigger_re is None:
            return False
        window = self.clause_window(text, start)
        if not window:
            return False
        if self._pseudo_re is not None:
            window = self._pseudo_re.sub(" ", window)
        return self._trigger_re.search(window) is not None
