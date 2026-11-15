"""Pull App Store reviews from Apple's public customer-reviews feed.

The feed returns up to 10 pages of 50 reviews (about 500 most-recent reviews)
per app per country.
"""

from __future__ import annotations

import time

import requests

from positioning_lab.models import Review

FEED_URL = (
    "https://itunes.apple.com/{country}/rss/customerreviews/"
    "page={page}/id={app_id}/sortby=mostrecent/json"
)
MAX_PAGES = 10


def _label(entry: dict, key: str) -> str:
    value = entry.get(key) or {}
    return str(value.get("label", "")).strip()


def parse_feed(payload: dict, app_id: str, app_name: str) -> list[Review]:
    """Turn one page of the feed into Review objects.

    Entries without a rating (the feed sometimes includes an app-info entry)
    are skipped. Author names are dropped on purpose.
    """
    entries = (payload.get("feed") or {}).get("entry") or []
    if isinstance(entries, dict):  # a page with a single review is not a list
        entries = [entries]

    reviews = []
    for entry in entries:
        rating = _label(entry, "im:rating")
        if not rating.isdigit():
            continue
        reviews.append(
            Review(
                review_id=_label(entry, "id"),
                app_id=str(app_id),
                app_name=app_name,
                rating=int(rating),
                title=_label(entry, "title"),
                text=_label(entry, "content"),
                version=_label(entry, "im:version"),
                date=_label(entry, "updated")[:10],
            )
        )
    return reviews


def fetch_reviews(
    app_id: str,
    app_name: str,
    country: str = "us",
    pages: int = MAX_PAGES,
    session: requests.Session | None = None,
    pause: float = 0.5,
) -> list[Review]:
    """Fetch up to `pages` pages of the most recent reviews for one app."""
    http = session or requests.Session()
    seen: set[str] = set()
    reviews: list[Review] = []

    for page in range(1, min(pages, MAX_PAGES) + 1):
        url = FEED_URL.format(country=country, page=page, app_id=app_id)
        response = http.get(url, timeout=30)
        if response.status_code != 200:
            break
        batch = parse_feed(response.json(), app_id, app_name)
        if not batch:
            break
        for review in batch:
            if review.review_id not in seen:
                seen.add(review.review_id)
                reviews.append(review)
        time.sleep(pause)

    return reviews
