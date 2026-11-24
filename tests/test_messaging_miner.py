import pytest

from ariadne_pmm.analyze.aggregate import build_frame, theme_shares
from ariadne_pmm.analyze.keyword_tagger import tag_review, tag_reviews_by_keywords
from ariadne_pmm.models import Review
from ariadne_pmm.pack import load_pack
from ariadne_pmm.report import render_battlecard

PACK = load_pack("messaging_miner")


def make_review(text, review_id="1", rating=5):
    return Review(review_id, "9", "Alpha", rating, "Title", text, "1.0", "2026-11-01")


def test_pack_reads_happy_reviews_and_every_theme_has_keywords():
    assert PACK.ratings == (4, 5)
    assert set(PACK.keywords) == set(PACK.themes) - {"other"}
    assert (PACK.title, PACK.subject) == ("What users love", "praise")


@pytest.mark.parametrize(
    ("text", "theme"),
    [
        ("So easy to use, my grandma figured it out.", "ease_of_use"),
        ("No ads at all, which is why I switched.", "no_ads"),
        ("It has every song I can think of.", "content_library"),
        ("The daily mix keeps finding new music I actually like.", "recommendations"),
        ("Lets me stay in touch with my friends every day.", "social_connection"),
        ("Lossless audio sounds incredible on my headphones.", "sound_quality"),
        ("Love it, great app!", "other"),
    ],
)
def test_praise_gets_the_expected_theme(text, theme):
    assert tag_review(make_review(text), PACK)["theme"] == theme


def test_report_uses_the_packs_wording():
    reviews = [make_review("No ads, worth every penny.", review_id=str(i)) for i in range(30)]
    tags = tag_reviews_by_keywords(reviews, PACK)
    frame = build_frame(reviews, tags, PACK)
    report = render_battlecard(frame, theme_shares(frame, PACK), PACK, run_date="2026-11-24")
    assert report.startswith("# What users love (2026-11-24)")
    assert "## Praise by theme" in report
    assert "Competitor weakness map" not in report


def test_weakness_map_wording_is_unchanged():
    pack = load_pack("weakness_map")
    assert (pack.title, pack.subject, pack.focus) == (
        "Competitor weakness map",
        "complaints",
        "main complaint",
    )
