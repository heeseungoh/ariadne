import json
from pathlib import Path

import requests

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


def no_sleep(seconds):
    pass


def test_fetch_reviews_stops_at_first_empty_page_after_retrying_it():
    session = FakeSession()
    reviews = fetch_reviews("123", "Demo", session=session, sleep=no_sleep)
    assert len(reviews) == 2
    assert session.calls == 4  # page 1, then page 2 tried 3 times


class FlakySession:
    """Page 2 fails twice (error, then empty) before it works; page 3 is the real end."""

    def __init__(self):
        self.page2_calls = 0

    def get(self, url, timeout):
        if "page=1/" in url:
            return FakeResponse(FIXTURE)
        if "page=2/" in url:
            self.page2_calls += 1
            if self.page2_calls == 1:
                return FakeResponse({}, status_code=503)
            if self.page2_calls == 2:
                return FakeResponse({"feed": {}})
            page = json.loads(json.dumps(FIXTURE))
            for i, entry in enumerate(page["feed"]["entry"]):
                entry["id"] = {"label": f"2{i}"}
            return FakeResponse(page)
        return FakeResponse({"feed": {}})


def test_fetch_reviews_retries_a_failed_page_and_keeps_going():
    session = FlakySession()
    reviews = fetch_reviews("123", "Demo", session=session, sleep=no_sleep)
    assert [r.review_id for r in reviews] == ["1001", "1002", "20", "21"]
    assert session.page2_calls == 3


class BrokenSession:
    def get(self, url, timeout):
        raise requests.ConnectionError("network down")


def test_fetch_reviews_survives_network_errors():
    assert fetch_reviews("123", "Demo", session=BrokenSession(), sleep=no_sleep) == []
