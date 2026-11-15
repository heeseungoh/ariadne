from ariadne_pmm.ingest.discover import (
    AppInfo,
    description_keywords,
    find_competitors,
    resolve_app,
    short_name,
)


def item(track_id, name, genre="Social Networking", ratings=1000, description=""):
    return {
        "trackId": track_id,
        "trackName": name,
        "primaryGenreName": genre,
        "userRatingCount": ratings,
        "averageUserRating": 4.5,
        "sellerName": "Seller",
        "description": description,
    }


SEED = item(1, "BeReal", description="Share real photos with friends. Real friends, real life.")


class FakeResponse:
    def __init__(self, results):
        self.status_code = 200
        self._results = results

    def json(self):
        return {"results": self._results}


class FakeSession:
    """Answers lookups and searches from a fixed table keyed by search term."""

    def __init__(self, searches):
        self.searches = searches
        self.terms = []

    def get(self, url, params, timeout):
        if "lookup" in url:
            return FakeResponse([SEED] if params["id"] == "1" else [])
        self.terms.append(params["term"])
        return FakeResponse(self.searches.get(params["term"], []))


SEARCHES = {
    "BeReal": [SEED, item(2, "Locket Widget", ratings=500000), item(3, "Poparazzi")],
    "photo sharing": [item(2, "Locket Widget", ratings=500000), item(4, "Dispo")],
    "real": [item(2, "Locket Widget", ratings=500000), item(5, "Real Estate", genre="Lifestyle")],
    "friends": [item(3, "Poparazzi")],
}


def test_resolve_by_id_and_by_name():
    session = FakeSession({"bereal": [item(9, "BeReal Clone"), SEED]})
    assert resolve_app("1", session=session).name == "BeReal"
    assert resolve_app("bereal", session=session).app_id == "1"
    assert resolve_app("999", session=session) is None


def test_description_keywords_skip_stopwords():
    words = description_keywords("Share real photos with friends. Real friends, real life.")
    assert words == ["real", "friends", "photos"]


def test_competitors_rank_by_hits_genre_and_size_and_exclude_seed():
    seed = resolve_app("1", session=FakeSession({}))
    ranked = find_competitors(
        seed, keywords=["photo sharing"], top=10, session=FakeSession(SEARCHES), min_hits=1
    )
    names = [c.app.name for c in ranked]
    assert "BeReal" not in names
    assert names[0] == "Locket Widget"  # found by 3 searches
    assert names[1] == "Poparazzi"  # found by 2 searches
    assert names.index("Dispo") < names.index("Real Estate")  # same genre wins the tie


def test_reason_explains_the_ranking():
    seed = resolve_app("1", session=FakeSession({}))
    top = find_competitors(seed, keywords=["photo sharing"], session=FakeSession(SEARCHES))[0]
    reason = top.reason(seed.genre)
    assert "found by 3 search(es)" in reason
    assert "same genre (Social Networking)" in reason
    assert "500,000 ratings" in reason


def test_each_query_runs_once_and_top_limits_results():
    seed = AppInfo("1", "BeReal", "Social Networking", 0, 0.0, "Seller", "real real")
    session = FakeSession(SEARCHES)
    ranked = find_competitors(seed, keywords=["BeReal", "real"], top=2, session=session, min_hits=1)
    assert session.terms == ["BeReal", "real"]
    assert len(ranked) == 2


def test_apps_found_by_a_single_search_are_dropped_by_default():
    seed = resolve_app("1", session=FakeSession({}))
    ranked = find_competitors(
        seed, keywords=["photo sharing"], top=10, session=FakeSession(SEARCHES)
    )
    assert [c.app.name for c in ranked] == ["Locket Widget", "Poparazzi"]


def test_short_name_drops_the_store_tagline():
    assert short_name("BeReal: Photos & Friends Daily") == "BeReal"
    assert short_name("Discord - Talk, Play, Hang Out") == "Discord"
    assert short_name("Instants, an Instagram app") == "Instants"
    assert short_name("Locket Widget") == "Locket Widget"
    assert short_name("Life360: Family Safety & GPS") == "Life360"
