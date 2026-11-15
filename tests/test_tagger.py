import json
from types import SimpleNamespace

from positioning_lab.analyze.tagger import tag_reviews
from positioning_lab.models import Review
from positioning_lab.pack import load_pack

PACK = load_pack("weakness_map")


def make_review(review_id, text, rating=1):
    return Review(review_id, "123", "Demo", rating, "Title", text, "1.0", "2026-10-01")


class FakeClient:
    """Stands in for the Anthropic client and replies with canned labels."""

    def __init__(self, labels):
        self.labels = labels
        self.calls = 0
        self.messages = self

    def create(self, **kwargs):
        self.calls += 1
        prompt = kwargs["messages"][0]["content"]
        reply = [label for label in self.labels if f'id="{label["id"]}"' in prompt]
        text = "Here you go:\n" + json.dumps(reply)
        return SimpleNamespace(content=[SimpleNamespace(text=text)])


def test_valid_label_is_kept():
    reviews = [make_review("1", "Ten songs before paying is not enough.")]
    client = FakeClient(
        [{"id": "1", "theme": "pricing_paywall", "quote": "ten songs before paying"}]
    )
    tags = tag_reviews(reviews, PACK, client)
    assert tags["1"]["theme"] == "pricing_paywall"
    assert tags["1"]["quote"] == "ten songs before paying"


def test_invented_theme_falls_back_to_other():
    reviews = [make_review("1", "It is bad.")]
    client = FakeClient([{"id": "1", "theme": "made_up_theme", "quote": "It is bad."}])
    assert tag_reviews(reviews, PACK, client)["1"]["theme"] == "other"


def test_quote_not_in_review_is_discarded():
    reviews = [make_review("1", "The app crashes on launch.")]
    client = FakeClient([{"id": "1", "theme": "bugs_crashes", "quote": "worst app I ever used"}])
    assert tag_reviews(reviews, PACK, client)["1"]["quote"] == ""


def test_review_missing_from_reply_still_gets_a_row():
    reviews = [make_review("1", "Crashes."), make_review("2", "Too many ads.")]
    client = FakeClient([{"id": "1", "theme": "bugs_crashes", "quote": "Crashes."}])
    tags = tag_reviews(reviews, PACK, client)
    assert tags["2"] == {"review_id": "2", "theme": "other", "quote": ""}


def test_cache_prevents_a_second_api_call(tmp_path):
    cache = tmp_path / "cache.jsonl"
    reviews = [make_review("1", "Crashes.")]
    client = FakeClient([{"id": "1", "theme": "bugs_crashes", "quote": "Crashes."}])
    first = tag_reviews(reviews, PACK, client, cache_path=cache)
    second = tag_reviews(reviews, PACK, client, cache_path=cache)
    assert first == second
    assert client.calls == 1


def test_reviews_are_sent_in_batches():
    reviews = [make_review(str(i), f"Problem number {i}.") for i in range(5)]
    client = FakeClient([])
    tag_reviews(reviews, PACK, client, batch_size=2)
    assert client.calls == 3
