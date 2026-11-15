import argparse
import json
from types import SimpleNamespace

import pytest

from ariadne_pmm.cli import load_reviews_file, main, parse_app, run_pack
from ariadne_pmm.models import Review


class FakeClient:
    """Labels every review as a paywall complaint, quoting its full text."""

    def __init__(self):
        self.messages = self

    def create(self, **kwargs):
        prompt = kwargs["messages"][0]["content"]
        ids = [part.split('"')[0] for part in prompt.split('<review id="')[1:]]
        reply = [{"id": i, "theme": "pricing_paywall", "quote": "paywall"} for i in ids]
        return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(reply))])


def test_parse_app():
    assert parse_app("6759358792:Shufl FM") == ("6759358792", "Shufl FM")
    with pytest.raises(argparse.ArgumentTypeError):
        parse_app("Shufl FM")


def test_run_pack_end_to_end(tmp_path):
    reviews = [
        Review("1", "9", "Alpha", 1, "Bad", "Hit a paywall at once.", "1.0", "2026-10-01"),
        Review("2", "9", "Alpha", 5, "Great", "Love it.", "1.0", "2026-10-02"),
    ]
    report = run_pack(
        "weakness_map",
        reviews,
        FakeClient(),
        tmp_path / "reports",
        tmp_path / "data",
        run_date="2026-11-15",
    )
    text = report.read_text()
    assert report.name == "weakness_map-2026-11-15.md"
    assert "pricing_paywall: 100% (1 of 1 reviews)" in text
    assert (tmp_path / "data" / "snapshots" / "weakness_map-2026-11-15.csv").exists()
    assert (tmp_path / "data" / "cache" / "weakness_map-v1.jsonl").exists()


def test_reviews_file_round_trip(tmp_path):
    review = Review("1", "9", "Alpha", 1, "Bad", "Text", "1.0", "2026-10-01")
    path = tmp_path / "reviews.json"
    path.write_text(json.dumps([review.to_dict()]))
    assert load_reviews_file(path) == [review]


def test_main_lists_packs(capsys):
    assert main(["packs"]) == 0
    assert "weakness_map" in capsys.readouterr().out


def test_main_requires_an_input_and_an_api_key(monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert main(["run", "weakness_map"]) == 2
    assert main(["run", "weakness_map", "--app", "123:Demo"]) == 2
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err
