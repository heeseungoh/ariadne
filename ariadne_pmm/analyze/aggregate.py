"""All the numbers. Plain pandas, no AI: every share is a count over a stated sample."""

from __future__ import annotations

import pandas as pd

from ariadne_pmm.models import Review
from ariadne_pmm.pack import Pack


def build_frame(reviews: list[Review], tags: dict[str, dict], pack: Pack) -> pd.DataFrame:
    """One row per review the pack reads, with its theme and quote attached."""
    rows = []
    for review in reviews:
        if review.rating not in pack.ratings or review.review_id not in tags:
            continue
        tag = tags[review.review_id]
        rows.append({**review.to_dict(), "theme": tag["theme"], "quote": tag["quote"]})
    columns = list(Review.__dataclass_fields__) + ["theme", "quote"]
    return pd.DataFrame(rows, columns=columns)


def theme_shares(frame: pd.DataFrame, pack: Pack) -> pd.DataFrame:
    """Per app and theme: count, the app's sample size n, and share = count / n."""
    columns = ["app_name", "theme", "count", "n", "share", "low_sample"]
    if frame.empty:
        return pd.DataFrame(columns=columns)

    counts = frame.groupby(["app_name", "theme"]).size().rename("count").reset_index()
    totals = frame.groupby("app_name").size().rename("n").reset_index()
    shares = counts.merge(totals, on="app_name")
    shares["share"] = shares["count"] / shares["n"]
    shares["low_sample"] = shares["n"] < pack.min_sample
    shares = shares.sort_values(["app_name", "count", "theme"], ascending=[True, False, True])
    return shares[columns].reset_index(drop=True)


def evidence(frame: pd.DataFrame, app_name: str, theme: str, limit: int = 3) -> pd.DataFrame:
    """The reviews behind one number, newest first, preferring ones with a verified quote."""
    rows = frame[(frame["app_name"] == app_name) & (frame["theme"] == theme)].copy()
    rows["has_quote"] = rows["quote"].str.len() > 0
    rows = rows.sort_values(["has_quote", "date"], ascending=[False, False])
    return rows.drop(columns="has_quote").head(limit)


def plan_samples(reviews: list[Review], pack: Pack) -> dict[str, tuple[int, str]]:
    """Per app: how many reviews the pack can read, and which sample tier that allows.

    Covers every app in `reviews`, including apps with nothing in scope, so the
    plan can be shown before any money is spent on labelling.
    """
    counts: dict[str, int] = {}
    for review in reviews:
        counts.setdefault(review.app_name, 0)
        if review.rating in pack.ratings:
            counts[review.app_name] += 1
    return {app: (n, pack.sample_tier(n)) for app, n in counts.items()}
