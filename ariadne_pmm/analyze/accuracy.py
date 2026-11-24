"""Measure how often the labeller agrees with a person.

1. `draw_sample` picks a random set of labelled reviews from a run's snapshot. The
   reviews go to a sheet with an empty `human_theme` column; the tool's labels go to
   a separate key, so the person labels without seeing them.
2. `agreement` compares the person's labels with the tool's.

Per theme it reports precision (when the tool says "pricing", how often the person
agreed) and recall (of the reviews the person called "pricing", how many the tool
caught), plus the most common mix-ups.
"""

from __future__ import annotations

from collections import Counter

import pandas as pd

SHEET_COLUMNS = ["review_id", "app_name", "rating", "title", "text", "human_theme"]
KEY_COLUMNS = ["review_id", "tool_theme"]


def draw_sample(
    snapshot: pd.DataFrame, n: int = 100, seed: int = 7
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (sheet for the person, key with the tool's labels), both in the same order."""
    picked = snapshot.sample(n=min(n, len(snapshot)), random_state=seed).reset_index(drop=True)
    picked["review_id"] = picked["review_id"].astype(str)
    sheet = picked.assign(human_theme="")[SHEET_COLUMNS]
    key = picked.rename(columns={"theme": "tool_theme"})[KEY_COLUMNS]
    return sheet, key


def agreement(sheet: pd.DataFrame, key: pd.DataFrame, themes: list[str]) -> dict:
    """Compare human and tool labels on the reviews the person labelled."""
    sheet = sheet.assign(review_id=sheet["review_id"].astype(str))
    key = key.assign(review_id=key["review_id"].astype(str))
    merged = sheet.merge(key, on="review_id")
    merged["human_theme"] = merged["human_theme"].fillna("").astype(str).str.strip()
    labelled = merged[merged["human_theme"] != ""]

    unknown = sorted(set(labelled["human_theme"]) - set(themes))
    if unknown:
        raise ValueError(f"Unknown themes in human_theme: {', '.join(unknown)}")

    n = len(labelled)
    agree = int((labelled["human_theme"] == labelled["tool_theme"]).sum())
    per_theme = []
    for theme in themes:
        tool_says = labelled["tool_theme"] == theme
        human_says = labelled["human_theme"] == theme
        both = int((tool_says & human_says).sum())
        if not tool_says.any() and not human_says.any():
            continue
        per_theme.append(
            {
                "theme": theme,
                "tool": int(tool_says.sum()),
                "human": int(human_says.sum()),
                "both": both,
                "precision": both / int(tool_says.sum()) if tool_says.any() else None,
                "recall": both / int(human_says.sum()) if human_says.any() else None,
            }
        )
    mixups = Counter(
        (row.human_theme, row.tool_theme)
        for row in labelled.itertuples()
        if row.human_theme != row.tool_theme
    )
    return {
        "labelled": n,
        "skipped": len(merged) - n,
        "agree": agree,
        "rate": agree / n if n else None,
        "per_theme": per_theme,
        "mixups": mixups.most_common(5),
    }


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"


def render_agreement(result: dict, label: str = "keyword labeller") -> str:
    n = result["labelled"]
    lines = ["# Accuracy check", ""]
    if not n:
        return "\n".join(lines + ["No reviews have a `human_theme` yet.", ""])
    headline = (
        f"The {label} agreed with a person on **{_pct(result['rate'])}** of {n} reviews "
        f"({result['agree']} of {n})."
    )
    lines += [headline, ""]
    if result["skipped"]:
        lines += [f"{result['skipped']} reviews in the sheet were left blank and not counted.", ""]
    lines += [
        "| Theme | Tool said | Person said | Both | Precision | Recall |",
        "|---|---|---|---|---|---|",
    ]
    for row in result["per_theme"]:
        lines.append(
            f"| {row['theme']} | {row['tool']} | {row['human']} | {row['both']} | "
            f"{_pct(row['precision'])} | {_pct(row['recall'])} |"
        )
    legend = (
        "Precision: when the tool chose this theme, how often the person agreed. "
        "Recall: of the reviews the person put in this theme, how many the tool caught."
    )
    lines += ["", legend, ""]
    if result["mixups"]:
        lines += ["## Most common mix-ups", ""]
        for (human, tool), count in result["mixups"]:
            lines.append(f"- Person said `{human}`, tool said `{tool}`: {count}")
        lines.append("")
    return "\n".join(lines)
