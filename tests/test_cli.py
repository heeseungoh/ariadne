import argparse
import json
from types import SimpleNamespace

import pytest

from ariadne_pmm.cli import (
    collect_reviews,
    discover_apps,
    load_reviews_file,
    main,
    parse_app,
    run_pack,
)
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


def bulk(app, count, rating, start):
    return [
        Review(
            str(start + i), app, app, rating, "Bad", "Hit a paywall at once.", "1.0", "2026-10-01"
        )
        for i in range(count)
    ]


def test_run_pack_end_to_end(tmp_path, capsys):
    reviews = (
        bulk("Alpha", 30, 1, 1000)  # enough for percentages
        + bulk("Beta", 12, 2, 2000)  # counts only
        + bulk("Gamma", 1, 1, 3000)  # the one-review app: listed, never labelled
        + bulk("Delta", 4, 5, 4000)  # nothing the pack reads
    )
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
    assert "pricing_paywall: 100% (30 of 30 reviews)" in text
    assert "pricing_paywall: 12 of 12 reviews" in text
    assert "Small sample: 12 reviews" in text
    assert "Too few reviews to rank themes: 1 (minimum 10)" in text
    assert "review 3000)" in text
    assert "No 1-3 star reviews were found for: Delta." in text

    cache = (tmp_path / "data" / "cache" / "weakness_map-v3.jsonl").read_text()
    assert '"3000"' not in cache  # the one-review app cost nothing to label
    assert len(cache.splitlines()) == 42
    assert (tmp_path / "data" / "snapshots" / "weakness_map-2026-11-15.csv").exists()

    out = capsys.readouterr().out
    assert "Gamma: 1 reviews: too few to rank themes" in out
    assert "Delta: 0 reviews: nothing to analyse, left out" in out


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


def test_discover_apps_returns_seed_first_and_prints_reasons(capsys):
    from tests.test_discover import SEARCHES, FakeSession

    apps = discover_apps("1", ["photo sharing"], top=2, country="us", session=FakeSession(SEARCHES))
    assert apps == [("1", "BeReal"), ("2", "Locket Widget"), ("3", "Poparazzi")]
    out = capsys.readouterr().out
    assert "Seed: BeReal (id 1, Social Networking" in out
    assert "1. Locket Widget (id 2): found by 3 search(es)" in out


def test_discover_apps_stops_when_seed_is_unknown():
    from tests.test_discover import FakeSession

    with pytest.raises(SystemExit, match="Could not find"):
        discover_apps("999", [], top=3, country="us", session=FakeSession({}))


def test_run_accepts_seed_as_input(monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert main(["run", "weakness_map", "--seed", "BeReal"]) == 2
    assert "ANTHROPIC_API_KEY" in capsys.readouterr().err


def test_collect_reviews_saves_raw_pull_and_prints_star_counts(tmp_path, capsys):
    def fake_fetch(app_id, name, country, pages):
        return [
            Review("1", app_id, name, 1, "Bad", "Text", "1.0", "2026-10-01"),
            Review("2", app_id, name, 1, "Bad", "Text", "1.0", "2026-10-02"),
            Review("3", app_id, name, 5, "Good", "Text", "1.0", "2026-10-03"),
        ]

    reviews = collect_reviews([("9", "Alpha")], "us", 1, tmp_path, fetch=fake_fetch)
    assert len(reviews) == 3
    assert (tmp_path / "raw" / "9.json").exists()
    out = capsys.readouterr().out
    assert "Alpha: pulled 3 reviews (1 star: 2, 2 star: 0, 3 star: 0, 4 star: 0, 5 star: 1)" in out


def test_fetch_needs_an_app_but_no_api_key(monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert main(["fetch"]) == 2
    assert "ANTHROPIC_API_KEY" not in capsys.readouterr().err


def test_keyword_tagger_runs_without_a_client_or_api_key(tmp_path):
    reviews = bulk("Alpha", 30, 1, 1000)
    report = run_pack(
        "weakness_map",
        reviews,
        None,
        tmp_path / "reports",
        tmp_path / "data",
        run_date="2026-11-15",
        tagger="keywords",
    )
    text = report.read_text()
    assert "labelled by keyword rules, with no AI" in text
    assert "pricing_paywall: 100% (30 of 30 reviews)" in text
    assert '"Hit a paywall at once."' in text
    assert not (tmp_path / "data" / "cache").exists()


def test_missing_api_key_message_points_to_the_free_tagger(monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert main(["run", "weakness_map", "--app", "123:Demo"]) == 2
    assert "--tagger keywords" in capsys.readouterr().err


def test_discover_apps_passes_exclude_through(capsys):
    from tests.test_discover import SEARCHES, FakeSession

    apps = discover_apps(
        "1", ["photo sharing"], top=2, country="us", session=FakeSession(SEARCHES), exclude=["2"]
    )
    assert ("2", "Locket Widget") not in apps
    assert apps[0] == ("1", "BeReal")


def test_exclude_is_accepted_by_every_command():
    from ariadne_pmm.cli import build_parser

    parser = build_parser()
    for argv in (
        ["discover", "Apple Music", "--exclude", "Shazam"],
        ["fetch", "--seed", "Apple Music", "--exclude", "Shazam"],
        ["run", "weakness_map", "--seed", "Apple Music", "--exclude", "Shazam"],
    ):
        assert parser.parse_args(argv).exclude == ["Shazam"]
