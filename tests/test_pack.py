import pytest

from ariadne_pmm.pack import available_packs, load_pack


def test_weakness_map_pack_loads():
    pack = load_pack("weakness_map")
    assert pack.ratings == (1, 2, 3)
    assert "pricing_paywall" in pack.themes
    assert "other" in pack.themes
    assert pack.cache_key == "weakness_map-v2"
    assert "weakness_map" in available_packs()


def test_unknown_pack_names_the_available_ones():
    with pytest.raises(FileNotFoundError, match="weakness_map"):
        load_pack("does_not_exist")


def test_pack_without_fallback_theme_is_rejected(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("name: bad\nquestion: q\nthemes:\n  pricing: Price\n")
    with pytest.raises(ValueError, match="other"):
        load_pack(str(bad))


def test_sample_tiers():
    pack = load_pack("weakness_map")
    assert [pack.sample_tier(n) for n in (0, 1, 9, 10, 29, 30, 500)] == [
        "none",
        "list",
        "list",
        "counts",
        "counts",
        "full",
        "full",
    ]
