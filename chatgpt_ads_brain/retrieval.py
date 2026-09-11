"""Deterministic offline normalization for Arabic/English ads retrieval."""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

MAX_TERMS = 200

_ARABIC_TRANSLATION = str.maketrans({
    "أ": "ا",
    "إ": "ا",
    "آ": "ا",
    "ٱ": "ا",
    "ى": "ي",
    "ؤ": "و",
    "ئ": "ي",
    "ـ": "",
})

# Expansions are deliberately small, advertising-specific, and local. They are
# applied to both queries and evidence so acronyms and spelling variants meet.
_TERM_ALIASES: dict[str, tuple[str, ...]] = {
    "cpa": ("cost", "acquisition", "conversion"),
    "cpc": ("cost", "click"),
    "cpm": ("cost", "impressions"),
    "ocpc": ("cpc", "conversion", "optimization"),
    "ocpm": ("cpm", "conversion", "optimization"),
    "ctr": ("click", "through", "rate"),
    "roas": ("return", "ad", "spend", "revenue"),
    "optimise": ("optimize", "optimization"),
    "optimised": ("optimized", "optimization"),
    "adgroup": ("ad", "group"),
    "تكلفة": ("cost",),
    "تكلفه": ("cost",),
    "التحويل": ("conversion",),
    "تحويل": ("conversion",),
    "التحويلات": ("conversion", "conversions"),
    "تحويلات": ("conversion", "conversions"),
    "الاكتساب": ("acquisition", "cpa"),
    "اكتساب": ("acquisition", "cpa"),
    "قياس": ("measurement",),
    "القياس": ("measurement",),
    "احسب": ("calculate",),
    "حساب": ("calculate",),
    "النقرات": ("click", "clicks"),
    "نقرات": ("click", "clicks"),
    "الانطباعات": ("impressions",),
    "انطباعات": ("impressions",),
    "الاسناد": ("attribution",),
    "اسناد": ("attribution",),
}


def normalize_text(text: str) -> str:
    """Normalize Unicode, Arabic letter variants, case, and punctuation."""
    value = unicodedata.normalize("NFKC", text).translate(_ARABIC_TRANSLATION).casefold()
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return " ".join(re.findall(r"\w+", value, flags=re.UNICODE))


def _bounded(values: Iterable[str], limit: int) -> set[str]:
    result: set[str] = set()
    for value in values:
        if value:
            result.add(value)
        if len(result) >= limit:
            break
    return result


def terms(text: str, *, limit: int = MAX_TERMS, expand_aliases: bool = True) -> set[str]:
    """Return bounded lexical terms, optionally expanding ads query aliases."""
    if limit < 1:
        return set()
    tokens = normalize_text(text).split()
    if not expand_aliases:
        return _bounded(tokens, limit)
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        expanded.extend(_TERM_ALIASES.get(token, ()))
    return _bounded(expanded, limit)
