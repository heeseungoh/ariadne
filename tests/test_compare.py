import pandas as pd

from ariadne_pmm.analyze.compare import compare_runs, render_comparison
from ariadne_pmm.cli import main
from ariadne_pmm.pack import load_pack

PACK = load_pack("weakness_map")


def run(app, counts):
    """A snapshot for one app: counts maps theme -> number of reviews."""
    rows, i = [], 0
    for theme, count in counts.items():
        for _ in range(count):
            rows.append({"review_id": f"{app}-{i}", "app_name": app, "theme": theme})
            i += 1
    return pd.DataFrame(rows)


def test_a_big_move_on_a_big_sample_is_likely_real():
    old = run("Apple Music", {"update_regression": 53, "other": 85})
    new = run("Apple Music", {"update_regression": 15, "other": 123})
    row = compare_runs(old, new, PACK).query("theme == 'update_regression'").iloc[0]
    assert round(row["change"], 3) == round(15 / 138 - 53 / 138, 3)
    assert bool(row["likely_real"]) is True


def test_a_small_move_is_noise():
    old = run("Spotify", {"ads": 41, "other": 97})
    new = run("Spotify", {"ads": 38, "other": 100})
    row = compare_runs(old, new, PACK).query("theme == 'ads'").iloc[0]
    assert bool(row["likely_real"]) is False


def test_a_big_move_on_a_tiny_sample_is_never_called_real():
    old = run("Pandora", {"ads": 1, "other": 9})
    new = run("Pandora", {"ads": 9, "other": 1})
    row = compare_runs(old, new, PACK).query("theme == 'ads'").iloc[0]
    assert bool(row["enough_sample"]) is False
    assert bool(row["likely_real"]) is False


def test_report_lists_real_changes_and_apps_in_only_one_run():
    old = pd.concat(
        [run("Apple Music", {"update_regression": 53, "other": 85}), run("Shazam", {"other": 40})]
    )
    new = run("Apple Music", {"update_regression": 15, "other": 123})
    diff = compare_runs(old, new, PACK)
    report = render_comparison(diff, "nov", "dec", only_old=["Shazam"], only_new=[])
    assert (
        "**Apple Music, update_regression:** down 28 points, from 38% (53 of 138) to 11% (15 of 138)"
        in report
    )
    assert "Only in nov: Shazam." in report


def test_compare_command(tmp_path):
    old_path, new_path = tmp_path / "old.csv", tmp_path / "new.csv"
    run("Alpha", {"ads": 40, "other": 60}).to_csv(old_path, index=False)
    run("Alpha", {"ads": 40, "other": 60}).to_csv(new_path, index=False)
    out = tmp_path / "compare.md"
    assert main(["compare", str(old_path), str(new_path), "--out", str(out)]) == 0
    assert "None. Every difference between the two runs is within sample noise." in out.read_text()
