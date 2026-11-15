"""Render the pack's deliverable as markdown."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from ariadne_pmm.analyze.aggregate import evidence
from ariadne_pmm.models import Review
from ariadne_pmm.pack import FALLBACK_THEME, Pack


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def _cell(count: int, n: int, tier: str) -> str:
    """One number in the comparison table, written as strongly as the sample allows."""
    return _pct(count / n) if tier == "full" else f"{count} of {n}"


def _review_line(review) -> str:
    quote = review["quote"] or review["text"][:160]
    return (
        f'- "{quote}" ({review["rating"]} stars, v{review["version"]}, '
        f"{review['date']}, review {review['review_id']})"
    )


def render_battlecard(
    frame: pd.DataFrame,
    shares: pd.DataFrame,
    pack: Pack,
    top_themes: int = 5,
    run_date: str | None = None,
    listed: list[Review] | None = None,
    empty_apps: list[str] | None = None,
    tagger: str = "claude",
) -> str:
    """Write the battlecard.

    `frame` and `shares` cover apps with enough reviews to rank themes.
    `listed` holds the reviews of apps with too few for that: they are shown
    as they are, unlabelled. `empty_apps` had no reviews the pack reads.
    """
    run_date = run_date or datetime.now(tz=timezone.utc).date().isoformat()
    listed = listed or []
    empty_apps = empty_apps or []
    stars = f"{min(pack.ratings)}-{max(pack.ratings)} star"
    if tagger == "keywords":
        how = (
            "by keyword rules, with no AI. The rules only match words, so expect some "
            "mislabelled reviews and a larger 'other' group than with the Claude labeller. "
            "Quotes are the sentence that matched."
        )
    else:
        how = "by Claude. Quotes are checked word for word against the review text."
    method = (
        f"**Method:** {len(frame)} {stars} App Store reviews, each given one theme from a "
        f"fixed list of {len(pack.themes)} (pack `{pack.cache_key}`), labelled {how} "
        f"An app needs {pack.min_sample} reviews for percentages and {pack.min_reviews} for "
        "theme counts; below that its reviews are listed without themes."
    )
    lines = [
        f"# Competitor weakness map ({run_date})",
        "",
        f"**Question:** {pack.question}",
        "",
        method,
        "",
    ]

    if shares.empty and not listed:
        lines.append("No reviews matched this pack.")
        return "\n".join(lines) + "\n"

    if not shares.empty:
        apps = sorted(shares["app_name"].unique())
        totals = {
            app: int(n) for app, n in shares.drop_duplicates("app_name")[["app_name", "n"]].values
        }
        tiers = {app: pack.sample_tier(totals[app]) for app in apps}
        counts = shares.pivot(index="theme", columns="app_name", values="count").fillna(0)
        share_grid = shares.pivot(index="theme", columns="app_name", values="share").fillna(0.0)
        order = share_grid.max(axis=1).sort_values(ascending=False).index

        lines += ["## Complaints by theme", ""]
        lines.append("| Theme | " + " | ".join(f"{app} (n={totals[app]})" for app in apps) + " |")
        lines.append("|---|" + "---|" * len(apps))
        for theme in order:
            cells = [_cell(int(counts.loc[theme, app]), totals[app], tiers[app]) for app in apps]
            lines.append(f"| {theme} | " + " | ".join(cells) + " |")
        lines.append("")

        for app in apps:
            n, tier = totals[app], tiers[app]
            app_shares = shares[(shares["app_name"] == app) & (shares["theme"] != FALLBACK_THEME)]
            lines += [f"## {app}", ""]
            if tier != "full":
                warning = (
                    f"> Small sample: {n} reviews (percentages need {pack.min_sample}). "
                    "Counts only. Treat as directional."
                )
                lines += [warning, ""]
            for _, row in app_shares.head(top_themes).iterrows():
                count = int(row["count"])
                if tier == "full":
                    heading = f"### {row['theme']}: {_pct(row['share'])} ({count} of {n} reviews)"
                else:
                    heading = f"### {row['theme']}: {count} of {n} reviews"
                lines += [heading, ""]
                lines += [_review_line(r) for _, r in evidence(frame, app, row["theme"]).iterrows()]
                lines.append("")

    by_app: dict[str, list[Review]] = {}
    for review in listed:
        by_app.setdefault(review.app_name, []).append(review)
    for app in sorted(by_app):
        reviews = sorted(by_app[app], key=lambda r: r.date, reverse=True)
        note = (
            f"> Too few reviews to rank themes: {len(reviews)} (minimum {pack.min_reviews}). "
            "They are listed as written, without themes."
        )
        lines += [f"## {app}", "", note, ""]
        for review in reviews:
            text = f"{review.title}. {review.text}".strip()[:300]
            lines.append(
                f'- "{text}" ({review.rating} stars, v{review.version}, {review.date}, '
                f"review {review.review_id})"
            )
        lines.append("")

    if empty_apps:
        lines += [
            "## Left out",
            "",
            f"No {stars} reviews were found for: {', '.join(sorted(empty_apps))}.",
            "",
        ]

    return "\n".join(lines) + "\n"
