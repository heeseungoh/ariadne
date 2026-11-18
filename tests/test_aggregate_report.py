from ariadne_pmm.analyze.aggregate import build_frame, evidence, plan_samples, theme_shares
from ariadne_pmm.models import Review
from ariadne_pmm.pack import load_pack
from ariadne_pmm.report import render_battlecard

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
    assert "pricing_paywall: 2 of 3 reviews" in report
    assert "67%" not in report  # too few reviews for a percentage
    assert "review 1)" in report
    assert "Small sample: 3 reviews" in report


def test_full_sample_gets_percentages():
    reviews = [make_review(str(i), "Alpha", 1, "Paywall.") for i in range(24)]
    reviews += [make_review(str(i), "Alpha", 2, "It crashes.") for i in range(24, 30)]
    tags = {
        r.review_id: {
            "review_id": r.review_id,
            "theme": "pricing_paywall" if r.rating == 1 else "bugs_crashes",
            "quote": "",
        }
        for r in reviews
    }
    frame = build_frame(reviews, tags, PACK)
    report = render_battlecard(frame, theme_shares(frame, PACK), PACK, run_date="2026-11-15")
    assert "pricing_paywall: 80% (24 of 30 reviews)" in report
    assert "| pricing_paywall | 80% |" in report
    assert "Small sample" not in report


def test_plan_samples_covers_every_app_including_empty_ones():
    reviews = [
        make_review("1", "Alpha", 1),
        make_review("2", "Alpha", 5),
        make_review("3", "Beta", 5),
    ]
    assert plan_samples(reviews, PACK) == {"Alpha": (1, "list"), "Beta": (0, "none")}


def test_report_shows_newest_unlabelled_reviews_up_to_the_limit():
    reviews = [
        make_review(str(i), "Alpha", 1, f"Odd complaint {i}.", date=f"2026-10-{i + 1:02d}")
        for i in range(12)
    ]
    tags = {r.review_id: {"review_id": r.review_id, "theme": "other", "quote": ""} for r in reviews}
    frame = build_frame(reviews, tags, PACK)
    report = render_battlecard(
        frame, theme_shares(frame, PACK), PACK, run_date="2026-11-17", unlabelled_sample=3
    )
    assert "### Matched no theme: 12 of 12" in report
    assert "Odd complaint 11." in report  # newest
    assert "Odd complaint 9." in report
    assert "Odd complaint 8." not in report  # past the limit of 3


def test_unlabelled_section_is_skipped_when_every_review_has_a_theme():
    reviews, tags = make_data()
    frame = build_frame(reviews, tags, PACK)
    report = render_battlecard(frame, theme_shares(frame, PACK), PACK, run_date="2026-11-17")
    assert "Matched no theme" not in report
