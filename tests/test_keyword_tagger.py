import pytest

from ariadne_pmm.analyze.keyword_tagger import tag_review, tag_reviews_by_keywords
from ariadne_pmm.models import Review
from ariadne_pmm.pack import Pack, load_pack

PACK = load_pack("weakness_map")


def make_review(text, title="Title", review_id="1"):
    return Review(review_id, "9", "Alpha", 1, title, text, "1.0", "2026-10-01")


def test_every_theme_but_other_has_keywords():
    assert set(PACK.keywords) == set(PACK.themes) - {"other"}


@pytest.mark.parametrize(
    ("text", "theme"),
    [
        ("They want a subscription for everything now. Too expensive.", "pricing_paywall"),
        ("The app crashes every time I open the camera.", "bugs_crashes"),
        ("Way too many ads between posts.", "ads"),
        ("I got logged out and my password no longer works.", "account_login"),
        ("Ever since the update it is worse. Bring back the old version.", "update_regression"),
        ("I love my dog.", "other"),
        # added in version 2, from reviews that matched no theme in the Apple Music study
        ("Way too many adds between every song.", "ads"),
        ("The app stops playing after each track.", "bugs_crashes"),
        ("Please give us the old red logo.", "update_regression"),
        ("It really needs a sleep timer.", "missing_feature"),
        ("My downloaded songs vanish when I go offline.", "sync_data_loss"),
        ("It plays the same songs on repeat and the recommendations are bad.", "content_quality"),
        ("You can only like a limited number of songs.", "pricing_paywall"),
        # version 3
        ("Please undo the color change.", "update_regression"),
        ("You cannot play a song without paying.", "pricing_paywall"),
        ("The layout looks terrible on my Duo phone.", "ux_confusing"),
    ],
)
def test_reviews_get_the_expected_theme(text, theme):
    assert tag_review(make_review(text), PACK)["theme"] == theme


def test_quote_is_a_verbatim_sentence_containing_a_keyword():
    review = make_review("I liked it at first. Then the app crashes daily. Sad.")
    tag = tag_review(review, PACK)
    assert tag["quote"] == "Then the app crashes daily."
    assert tag["quote"] in review.text


def test_keywords_match_whole_word_starts_only():
    # "bads" must not count as "ads", and "price" inside "caprice" must not count
    assert tag_review(make_review("Such bads vibes and caprice."), PACK)["theme"] == "other"


def test_tie_goes_to_the_theme_listed_first():
    tag = tag_review(make_review("One subscription and one crash."), PACK)
    assert tag["theme"] == "pricing_paywall"


def test_same_input_gives_same_output():
    reviews = [
        make_review("Too many ads.", review_id="1"),
        make_review("It is slow.", review_id="2"),
    ]
    first = tag_reviews_by_keywords(reviews, PACK)
    assert first == tag_reviews_by_keywords(reviews, PACK)
    assert first["2"]["theme"] == "performance"


def test_pack_without_keywords_is_rejected():
    bare = Pack("bare", 1, "q", "report", (1,), 10, 30, {"other": "x"})
    with pytest.raises(ValueError, match="no keyword rules"):
        tag_reviews_by_keywords([make_review("text")], bare)
