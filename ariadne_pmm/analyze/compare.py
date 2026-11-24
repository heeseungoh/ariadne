"""Compare two runs of the same pack: what moved, and is the move bigger than noise?

A change is marked "likely real" only when both runs have at least the pack's
`min_sample` reviews for that app and a two-proportion z-test gives |z| >= 1.96
(roughly 95% confidence). Anything else is shown but not called a trend.
"""

from __future__ import annotations

import math

import pandas as pd

from ariadne_pmm.pack import Pack

Z_CUTOFF = 1.96


def _z(count_a: int, n_a: int, count_b: int, n_b: int) -> float:
    pooled = (count_a + count_b) / (n_a + n_b)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n_a + 1 / n_b))
    return 0.0 if se == 0 else (count_b / n_b - count_a / n_a) / se


def compare_runs(old: pd.DataFrame, new: pd.DataFrame, pack: Pack) -> pd.DataFrame:
    """One row per app and theme seen in either run, with shares, change and a verdict."""
    rows = []
    for app in sorted(set(old["app_name"]) & set(new["app_name"])):
        a, b = old[old["app_name"] == app], new[new["app_name"] == app]
        n_a, n_b = len(a), len(b)
        for theme in sorted(set(a["theme"]) | set(b["theme"])):
            count_a = int((a["theme"] == theme).sum())
            count_b = int((b["theme"] == theme).sum())
            enough = n_a >= pack.min_sample and n_b >= pack.min_sample
            z = _z(count_a, n_a, count_b, n_b)
            rows.append(
                {
                    "app_name": app,
                    "theme": theme,
                    "old_count": count_a,
                    "old_n": n_a,
                    "new_count": count_b,
                    "new_n": n_b,
                    "old_share": count_a / n_a,
                    "new_share": count_b / n_b,
                    "change": count_b / n_b - count_a / n_a,
                    "z": z,
                    "likely_real": enough and abs(z) >= Z_CUTOFF,
                    "enough_sample": enough,
                }
            )
    return pd.DataFrame(rows)


def render_comparison(
    diff: pd.DataFrame,
    old_label: str,
    new_label: str,
    only_old: list[str],
    only_new: list[str],
    top: int = 5,
) -> str:
    method = (
        "Shares are of each app's reviews in that run. A change is marked **likely real** only "
        "when both runs have enough reviews and the change is bigger than sample noise "
        "(two-proportion z-test, about 95% confidence)."
    )
    lines = [f"# What changed: {old_label} to {new_label}", "", method, ""]
    real = diff[diff["likely_real"]].sort_values("change", key=abs, ascending=False)
    lines += ["## Likely real changes", ""]
    if real.empty:
        lines += ["None. Every difference between the two runs is within sample noise.", ""]
    else:
        for _, row in real.iterrows():
            direction = "up" if row["change"] > 0 else "down"
            lines.append(
                f"- **{row['app_name']}, {row['theme']}:** {direction} {abs(row['change']) * 100:.0f} "
                f"points, from {row['old_share'] * 100:.0f}% ({row['old_count']} of {row['old_n']}) "
                f"to {row['new_share'] * 100:.0f}% ({row['new_count']} of {row['new_n']})"
            )
        lines.append("")

    for app in sorted(diff["app_name"].unique()):
        rows = diff[diff["app_name"] == app].sort_values("change", key=abs, ascending=False)
        first = rows.iloc[0]
        lines += [f"## {app} (n={first['old_n']} then {first['new_n']})", ""]
        if not first["enough_sample"]:
            lines += ["> Too few reviews in at least one run to call any change real.", ""]
        lines += ["| Theme | Before | After | Change |", "|---|---|---|---|"]
        for _, row in rows.head(top).iterrows():
            mark = " (likely real)" if row["likely_real"] else ""
            lines.append(
                f"| {row['theme']} | {row['old_share'] * 100:.0f}% | {row['new_share'] * 100:.0f}% | "
                f"{row['change'] * 100:+.0f} pts{mark} |"
            )
        lines.append("")

    for label, apps in ((old_label, only_old), (new_label, only_new)):
        if apps:
            lines += [f"Only in {label}: {', '.join(sorted(apps))}.", ""]
    return "\n".join(lines)
