import pandas as pd
import pytest

from ariadne_pmm.analyze.accuracy import agreement, draw_sample, render_agreement
from ariadne_pmm.cli import main

THEMES = ["pricing_paywall", "ads", "bugs_crashes", "other"]


def make_snapshot(n=20):
    themes = ["pricing_paywall", "ads", "bugs_crashes", "other"]
    return pd.DataFrame(
        {
            "review_id": [str(1000 + i) for i in range(n)],
            "app_id": "9",
            "app_name": "Alpha",
            "rating": 1,
            "title": [f"Title {i}" for i in range(n)],
            "text": [f"Review text {i}" for i in range(n)],
            "version": "1.0",
            "date": "2026-11-01",
            "source": "app_store",
            "theme": [themes[i % 4] for i in range(n)],
            "quote": "",
        }
    )


def test_sample_hides_the_tool_label_and_is_repeatable():
    sheet, key = draw_sample(make_snapshot(), n=8, seed=3)
    assert list(sheet.columns) == [
        "review_id",
        "app_name",
        "rating",
        "title",
        "text",
        "human_theme",
    ]
    assert "theme" not in sheet.columns and "tool_theme" not in sheet.columns
    assert list(key["review_id"]) == list(sheet["review_id"])
    again, _ = draw_sample(make_snapshot(), n=8, seed=3)
    assert list(again["review_id"]) == list(sheet["review_id"])


def test_sample_never_asks_for_more_than_exist():
    sheet, _ = draw_sample(make_snapshot(5), n=100)
    assert len(sheet) == 5


def test_agreement_counts_precision_recall_and_mixups():
    key = pd.DataFrame(
        {
            "review_id": ["1", "2", "3", "4", "5"],
            "tool_theme": ["ads", "ads", "pricing_paywall", "other", "ads"],
        }
    )
    sheet = pd.DataFrame(
        {
            "review_id": ["1", "2", "3", "4", "5"],
            "human_theme": ["ads", "pricing_paywall", "pricing_paywall", "other", ""],
        }
    )
    result = agreement(sheet, key, THEMES)
    assert (result["labelled"], result["skipped"], result["agree"]) == (4, 1, 3)
    assert result["rate"] == 0.75
    ads = next(row for row in result["per_theme"] if row["theme"] == "ads")
    assert (ads["tool"], ads["human"], ads["both"]) == (2, 1, 1)
    assert ads["precision"] == 0.5 and ads["recall"] == 1.0
    assert result["mixups"] == [(("pricing_paywall", "ads"), 1)]
    report = render_agreement(result)
    assert "**75%** of 4 reviews (3 of 4)" in report
    assert "1 reviews in the sheet were left blank" in report


def test_agreement_rejects_a_misspelled_theme():
    key = pd.DataFrame({"review_id": ["1"], "tool_theme": ["ads"]})
    sheet = pd.DataFrame({"review_id": ["1"], "human_theme": ["add"]})
    with pytest.raises(ValueError, match="add"):
        agreement(sheet, key, THEMES)


def test_sample_and_agree_commands_end_to_end(tmp_path, capsys):
    snapshot = tmp_path / "weakness_map-2026-11-18.csv"
    make_snapshot().to_csv(snapshot, index=False)
    out = tmp_path / "accuracy"

    assert main(["sample", str(snapshot), "--n", "10", "--out", str(out)]) == 0
    sheet_path = out / "weakness_map-2026-11-18-sheet.csv"
    assert "Fill in human_theme with one of: pricing_paywall" in capsys.readouterr().out

    # the person copies the tool's label on every review: full agreement
    sheet = pd.read_csv(sheet_path, dtype={"review_id": str})
    key = pd.read_csv(out / "weakness_map-2026-11-18-key.csv", dtype={"review_id": str})
    sheet["human_theme"] = key["tool_theme"]
    sheet.to_csv(sheet_path, index=False)

    report = tmp_path / "accuracy.md"
    assert main(["agree", str(sheet_path), "--out", str(report)]) == 0
    assert "**100%** of 10 reviews" in report.read_text()
