"""Find an app's competitors with Apple's public iTunes Search and Lookup APIs.

Apple does not publish a "competitors" list, so this builds one in three steps:

1. Resolve the seed app (by App Store ID or by name).
2. Search the App Store with several queries: the seed's name, any keywords
   you pass, and keywords taken from the seed's own description.
3. Score every app that came back, and keep the top N.

The score is deliberately simple and every part of it is reported, so you can
see why an app made the list and drop it if it doesn't belong:

- appeared in more of the searches  -> more likely a real substitute
- same primary genre as the seed    -> same shelf in the store
- more ratings                      -> bigger, better-known alternative
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

import requests

SEARCH_URL = "https://itunes.apple.com/search"
LOOKUP_URL = "https://itunes.apple.com/lookup"

_STOPWORD_TEXT = """
    a about above after again all also an and any app apps are as at be because been
    before being best both but by can could day did do does doing down during each easy
    every few for free from get gets has have having help here how if in into is it its
    just like make makes more most my new no not now of off on once one only or other our
    out over own same see share should so some such than that the their them then there
    these they this those through to too under until up use using very want was way we
    were what when where which while who why will with you your yours
"""
STOPWORDS = set(_STOPWORD_TEXT.split())


@dataclass
class AppInfo:
    app_id: str
    name: str
    genre: str
    rating_count: int
    rating: float
    seller: str
    description: str = ""


@dataclass
class Candidate:
    app: AppInfo
    query_hits: int = 0
    matched_queries: list[str] = field(default_factory=list)
    score: float = 0.0

    def reason(self, seed_genre: str) -> str:
        parts = [f"found by {self.query_hits} search(es): {', '.join(self.matched_queries)}"]
        if self.app.genre == seed_genre:
            parts.append(f"same genre ({seed_genre})")
        parts.append(f"{self.app.rating_count:,} ratings")
        return "; ".join(parts)


def short_name(name: str) -> str:
    """Drop the store tagline: 'BeReal: Photos & Friends Daily' becomes 'BeReal'."""
    head = re.split(r":\s|\s[-–—|]\s|,\s", name.strip(), maxsplit=1)[0].strip()
    return head or name.strip()


def _to_app(item: dict) -> AppInfo:
    return AppInfo(
        app_id=str(item.get("trackId", "")),
        name=str(item.get("trackName", "")).strip(),
        genre=str(item.get("primaryGenreName", "")),
        rating_count=int(item.get("userRatingCount") or 0),
        rating=float(item.get("averageUserRating") or 0.0),
        seller=str(item.get("sellerName", "")),
        description=str(item.get("description", "")),
    )


def _get(http, url: str, params: dict) -> list[dict]:
    response = http.get(url, params=params, timeout=30)
    if response.status_code != 200:
        return []
    return [r for r in response.json().get("results", []) if r.get("trackId")]


def resolve_app(query: str, country: str = "us", session=None) -> AppInfo | None:
    """Turn an App Store ID or an app name into the app's details."""
    http = session or requests.Session()
    query = query.strip()
    if query.isdigit():
        results = _get(http, LOOKUP_URL, {"id": query, "country": country})
    else:
        results = _get(
            http,
            SEARCH_URL,
            {"term": query, "country": country, "entity": "software", "limit": 10},
        )
        exact = [r for r in results if str(r.get("trackName", "")).lower() == query.lower()]
        results = exact or results
    return _to_app(results[0]) if results else None


def description_keywords(description: str, limit: int = 3) -> list[str]:
    """The most frequent meaningful words in an app's description."""
    words = re.findall(r"[a-z][a-z']{3,}", description.lower())
    counts = Counter(w for w in words if w not in STOPWORDS)
    return [word for word, _ in counts.most_common(limit)]


def score_candidates(seed: AppInfo, candidates: dict[str, Candidate]) -> list[Candidate]:
    ranked = []
    for candidate in candidates.values():
        if candidate.app.app_id == seed.app_id:
            continue
        genre_bonus = 2.0 if candidate.app.genre == seed.genre else 0.0
        popularity = math.log10(candidate.app.rating_count + 1)
        candidate.score = round(2.0 * candidate.query_hits + genre_bonus + 0.5 * popularity, 3)
        ranked.append(candidate)
    return sorted(ranked, key=lambda c: (-c.score, -c.app.rating_count, c.app.name))


def find_competitors(
    seed: AppInfo,
    keywords: list[str] | None = None,
    top: int = 5,
    country: str = "us",
    session=None,
    min_hits: int = 2,
) -> list[Candidate]:
    """Return the top competitors to the seed app, best first.

    An app must be found by at least `min_hits` different searches. One search
    alone lets in big apps that only share a keyword (a live run for BeReal let
    in Facebook, Discord and Life360 this way). Fewer than `top` apps may come
    back: a short honest list beats a padded one.
    """
    http = session or requests.Session()
    queries = [seed.name, *(keywords or []), *description_keywords(seed.description)]
    queries = list(dict.fromkeys(q.strip() for q in queries if q and q.strip()))

    candidates: dict[str, Candidate] = {}
    for query in queries:
        results = _get(
            http,
            SEARCH_URL,
            {"term": query, "country": country, "entity": "software", "limit": 50},
        )
        for item in results:
            app = _to_app(item)
            candidate = candidates.setdefault(app.app_id, Candidate(app=app))
            if query not in candidate.matched_queries:
                candidate.query_hits += 1
                candidate.matched_queries.append(query)

    ranked = [c for c in score_candidates(seed, candidates) if c.query_hits >= min_hits]
    return ranked[:top]
