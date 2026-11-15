import json
from pathlib import Path

from ariadne_pmm.ingest.app_store import fetch_reviews, parse_feed

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "app_store_page.json").read_text())


def test_parse_feed_keeps_only_rated_entries():
    reviews = parse_feed(FIXTURE, "123", "Demo")
    assert [r.review_id for r in reviews] == ["1001", "1002"]
    assert reviews[0].rating == 1
    assert reviews[0].version == "1.4.0"
    assert reviews[0].date == "2026-10-10"


def test_parse_feed_never_stores_author_names():
    reviews = parse_feed(FIXTURE, "123", "Demo")
    assert "someuser123" not in json.dumps([r.to_dict() for r in reviews])


def test_parse_feed_handles_single_entry_and_empty_page():
    single = {"feed": {"entry": FIXTURE["feed"]["entry"][0]}}
    assert len(parse_feed(single, "123", "Demo")) == 1
    assert parse_feed({"feed": {}}, "123", "Demo") == []


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeSession:
    """Serves the fixture on page 1 and an empty page after that."""

    def __init__(self):
        self.calls = 0

    def get(self, url, timeout):
        self.calls += 1
        return FakeResponse(FIXTURE if "page=1/" in url else {"feed": {}})


def test_fetch_reviews_stops_at_first_empty_page():
    session = FakeSession()
    reviews = fetch_reviews("123", "Demo", session=session, pause=0)
    assert len(reviews) == 2
    assert session.calls == 2
