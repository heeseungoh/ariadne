from positioning_lab.analyze.aggregate import build_frame, evidence, theme_shares
from positioning_lab.models import Review
from positioning_lab.pack import load_pack
from positioning_lab.report import render_battlecard

PACK = load_pack("weakness_map")


def make_review(review_id, app, rating, text="Some text", date="2026-10-01"):
    return Review(review_id, app, app, rating, "Title", text, "1.0", date)


def make_data():
    reviews = [
        make_review("1", "Alpha", 1, "Ten songs then a paywall."),
        make_review("2", "Alpha", 2, "Paywall right after setup.", date="2026-10-05"),
        make_review("3", "Alpha", 3, "It crashes."),
        make_review("4", "Alpha", 5, "Love it."),
        make_review("5", "Beta", 1, "Ads everywhere."),
    ]
    tags = {
        "1": {"review_id": "1", "theme": "pricing_paywall", "quote": "Ten songs then a paywall."},
        "2": {"review_id": "2", "theme": "pricing_paywall", "quote": ""},
        "3": {"review_id": "3", "theme": "bugs_crashes", "quote": "It crashes."},
        "4": {"review_id": "4", "theme": "other", "quote": ""},
        "5": {"review_id": "5", "theme": "ads", "quote": "Ads everywhere."},
    }
    return reviews, tags


def test_frame_keeps_only_ratings_the_pack_reads():
    reviews, tags = make_data()
    frame = build_frame(reviews, tags, PACK)
    assert sorted(frame["review_id"]) == ["1", "2", "3", "5"]


def test_shares_are_counts_over_sample_size():
    reviews, tags = make_data()
    shares = theme_shares(build_frame(reviews, tags, PACK), PACK)
    alpha = shares[(shares["app_name"] == "Alpha") & (shares["theme"] == "pricing_paywall")].iloc[0]
    assert (alpha["count"], alpha["n"]) == (2, 3)
    assert round(alpha["share"], 4) == 0.6667
    assert bool(alpha["low_sample"]) is True


def test_shares_sum_to_one_per_app():
    reviews, tags = make_data()
    shares = theme_shares(build_frame(reviews, tags, PACK), PACK)
    sums = shares.groupby("app_name")["share"].sum()
    assert all(abs(total - 1.0) < 1e-9 for total in sums)


def test_evidence_prefers_reviews_with_a_verified_quote():
    reviews, tags = make_data()
    rows = evidence(build_frame(reviews, tags, PACK), "Alpha", "pricing_paywall")
    assert list(rows["review_id"]) == ["1", "2"]


def test_empty_input_does_not_crash():
    frame = build_frame([], {}, PACK)
    shares = theme_shares(frame, PACK)
    assert shares.empty
    assert "No reviews matched" in render_battlecard(frame, shares, PACK)


def test_battlecard_shows_numbers_sample_sizes_and_review_ids():
    reviews, tags = make_data()
    frame = build_frame(reviews, tags, PACK)
    report = render_battlecard(frame, theme_shares(frame, PACK), PACK, run_date="2026-11-15")
    assert "Alpha (n=3)" in report
    assert "pricing_paywall: 67% (2 of 3 reviews)" in report
    assert "review 1)" in report
    assert "Low sample: only 3 reviews" in report
