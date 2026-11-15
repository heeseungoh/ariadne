"""Render the pack's deliverable as markdown."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from positioning_lab.analyze.aggregate import evidence
from positioning_lab.pack import FALLBACK_THEME, Pack


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def render_battlecard(
    frame: pd.DataFrame,
    shares: pd.DataFrame,
    pack: Pack,
    top_themes: int = 5,
    run_date: str | None = None,
) -> str:
    run_date = run_date or datetime.now(tz=timezone.utc).date().isoformat()
    stars = f"{min(pack.ratings)}-{max(pack.ratings)} star"
    method = (
        f"**Method:** {len(frame)} {stars} App Store reviews, each labelled with one theme "
        f"from a fixed list of {len(pack.themes)} (pack `{pack.cache_key}`). "
        "Shares are counts divided by each app's sample size n. "
        "Quotes are checked word for word against the review text."
    )
    lines = [
        f"# Competitor weakness map ({run_date})",
        "",
        f"**Question:** {pack.question}",
        "",
        method,
        "",
        "## Share of complaints by theme",
        "",
    ]

    if shares.empty:
        lines.append("No reviews matched this pack.")
        return "\n".join(lines) + "\n"

    apps = sorted(shares["app_name"].unique())
    totals = shares.drop_duplicates("app_name").set_index("app_name")["n"]
    grid = shares.pivot(index="theme", columns="app_name", values="share").fillna(0.0)
    grid = grid.loc[grid.max(axis=1).sort_values(ascending=False).index]

    lines.append("| Theme | " + " | ".join(f"{app} (n={totals[app]})" for app in apps) + " |")
    lines.append("|---|" + "---|" * len(apps))
    for theme, row in grid.iterrows():
        lines.append(f"| {theme} | " + " | ".join(_pct(row[app]) for app in apps) + " |")
    lines.append("")

    for app in apps:
        app_shares = shares[(shares["app_name"] == app) & (shares["theme"] != FALLBACK_THEME)]
        n = int(totals[app])
        lines += [f"## {app}", ""]
        if n < pack.min_sample:
            warning = (
                f"> Low sample: only {n} reviews (minimum {pack.min_sample}). "
                "Treat these shares as directional."
            )
            lines += [warning, ""]
        for _, row in app_shares.head(top_themes).iterrows():
            lines.append(
                f"### {row['theme']}: {_pct(row['share'])} ({int(row['count'])} of {n} reviews)"
            )
            lines.append("")
            for _, review in evidence(frame, app, row["theme"]).iterrows():
                quote = review["quote"] or review["text"][:160]
                lines.append(
                    f'- "{quote}" ({review["rating"]} stars, v{review["version"]}, '
                    f"{review['date']}, review {review['review_id']})"
                )
            lines.append("")

    return "\n".join(lines) + "\n"
