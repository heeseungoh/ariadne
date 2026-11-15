"""Label reviews with the pack's keyword rules. Free: no API key, no AI.

This is the fallback labeller. It is fully repeatable and costs nothing, but it
only sees words, not meaning: "I wish it would stop crashing" counts a hit for
both missing_feature ("wish") and bugs_crashes ("crash"). Expect it to be less
accurate than the Claude labeller, and to leave more reviews in "other".
"""

from __future__ import annotations

import re
from functools import cache

from ariadne_pmm.models import Review
from ariadne_pmm.pack import FALLBACK_THEME, Pack

MAX_QUOTE = 200


@cache
def _pattern(keyword: str) -> re.Pattern:
    return re.compile(r"\b" + re.escape(keyword), re.IGNORECASE)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def tag_review(review: Review, pack: Pack) -> dict:
    text = f"{review.title}. {review.text}"
    best_theme, best_hits, best_keywords = FALLBACK_THEME, 0, ()
    for theme, keywords in pack.keywords.items():
        matched = tuple(k for k in keywords if _pattern(k).search(text))
        if len(matched) > best_hits:  # strict: on a tie the earlier theme wins
            best_theme, best_hits, best_keywords = theme, len(matched), matched

    quote = ""
    if best_keywords:
        for sentence in _sentences(review.text) + _sentences(review.title):
            if any(_pattern(k).search(sentence) for k in best_keywords):
                quote = sentence[:MAX_QUOTE]
                break
    return {"review_id": review.review_id, "theme": best_theme, "quote": quote}


def tag_reviews_by_keywords(reviews: list[Review], pack: Pack) -> dict[str, dict]:
    """Return {review_id: {"review_id", "theme", "quote"}}, same shape as the Claude labeller."""
    if not pack.keywords:
        raise ValueError(
            f"Pack '{pack.name}' has no keyword rules, so it needs the Claude labeller"
        )
    return {review.review_id: tag_review(review, pack) for review in reviews}
