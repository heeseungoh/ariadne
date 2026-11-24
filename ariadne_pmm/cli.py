"""Command line entry point: run a research pack on a set of apps."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ariadne_pmm.analyze.accuracy import agreement, draw_sample, render_agreement
from ariadne_pmm.analyze.aggregate import build_frame, plan_samples, theme_shares
from ariadne_pmm.analyze.compare import compare_runs, render_comparison
from ariadne_pmm.analyze.keyword_tagger import tag_reviews_by_keywords
from ariadne_pmm.analyze.tagger import DEFAULT_MODEL, tag_reviews
from ariadne_pmm.ingest.app_store import fetch_reviews
from ariadne_pmm.ingest.discover import find_competitors, resolve_app, short_name
from ariadne_pmm.models import Review
from ariadne_pmm.pack import Pack, available_packs, load_pack
from ariadne_pmm.report import render_battlecard


def parse_app(value: str) -> tuple[str, str]:
    """Parse an --app value written as APP_ID:Name."""
    app_id, _, name = value.partition(":")
    if not app_id.strip().isdigit() or not name.strip():
        raise argparse.ArgumentTypeError(f"'{value}' should look like 6759358792:Shufl FM")
    return app_id.strip(), name.strip()


def discover_apps(
    seed_query: str,
    keywords: list[str],
    top: int,
    country: str,
    session=None,
    exclude: list[str] | None = None,
) -> list[tuple[str, str]]:
    """Resolve the seed app, find its competitors, print why each was picked.

    Returns the seed plus competitors as (app_id, name) pairs.
    """
    seed = resolve_app(seed_query, country=country, session=session)
    if seed is None:
        raise SystemExit(f"Could not find an App Store app matching '{seed_query}'.")

    print(f"Seed: {seed.name} (id {seed.app_id}, {seed.genre}, {seed.rating_count:,} ratings)")
    competitors = find_competitors(
        seed, keywords=keywords, top=top, country=country, session=session, exclude=exclude
    )
    for rank, candidate in enumerate(competitors, start=1):
        app = candidate.app
        print(f"{rank}. {app.name} (id {app.app_id}): {candidate.reason(seed.genre)}")
    apps = [seed, *(c.app for c in competitors)]
    return [(app.app_id, short_name(app.name)) for app in apps]


def collect_reviews(
    apps: list[tuple[str, str]], country: str, pages: int, data_dir: Path, fetch=fetch_reviews
) -> list[Review]:
    """Pull reviews for each app, save the raw pull locally, and print counts by star rating."""
    reviews: list[Review] = []
    for app_id, name in apps:
        pulled = fetch(app_id, name, country=country, pages=pages)
        stars = Counter(r.rating for r in pulled)
        by_star = ", ".join(f"{star} star: {stars.get(star, 0)}" for star in range(1, 6))
        print(f"{name}: pulled {len(pulled)} reviews ({by_star})")
        wanted = min(pages, 10) * 50
        if len(pulled) < wanted:
            print(
                f"  Note: {name} returned {len(pulled)} of up to {wanted} reviews. Either the app "
                "has fewer recent reviews, or Apple's feed stopped early. Re-run later to check."
            )
        raw = data_dir / "raw" / f"{app_id}.json"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text(json.dumps([r.to_dict() for r in pulled], indent=2))
        reviews.extend(pulled)
    return reviews


def load_reviews_file(path: Path) -> list[Review]:
    return [Review(**row) for row in json.loads(path.read_text())]


PLAN_NOTES = {
    "none": "nothing to analyse, left out",
    "list": "too few to rank themes, reviews will be listed and not labelled",
    "counts": "small sample, counts only",
    "full": "full percentages",
}


def print_sample_plan(reviews: list[Review], pack: Pack) -> dict[str, tuple[int, str]]:
    """Show, per app, how many reviews the pack can read and what that sample allows."""
    plan = plan_samples(reviews, pack)
    stars = f"{min(pack.ratings)}-{max(pack.ratings)} star"
    print(f"Sample check for pack '{pack.name}' ({stars} reviews):")
    for app, (n, tier) in plan.items():
        print(f"  {app}: {n} reviews: {PLAN_NOTES[tier]}")
    return plan


def run_pack(
    pack_name: str,
    reviews: list[Review],
    client,
    out_dir: Path,
    data_dir: Path,
    model: str = DEFAULT_MODEL,
    run_date: str | None = None,
    tagger: str = "claude",
) -> Path:
    """Check samples, tag, count and write the report. Returns the report path.

    Only apps with enough reviews to rank themes are sent for labelling.
    `tagger` is "claude" (needs `client`) or "keywords" (free, `client` unused).
    """
    pack = load_pack(pack_name)
    run_date = run_date or datetime.now(tz=timezone.utc).date().isoformat()
    plan = print_sample_plan(reviews, pack)
    in_scope = [r for r in reviews if r.rating in pack.ratings]
    to_tag = [r for r in in_scope if plan[r.app_name][1] in ("counts", "full")]
    listed = [r for r in in_scope if plan[r.app_name][1] == "list"]
    empty_apps = [app for app, (_, tier) in plan.items() if tier == "none"]

    if tagger == "keywords":
        tags = tag_reviews_by_keywords(to_tag, pack)
    else:
        tags = tag_reviews(
            to_tag,
            pack,
            client,
            cache_path=data_dir / "cache" / f"{pack.cache_key}.jsonl",
            model=model,
        )
    frame = build_frame(to_tag, tags, pack)
    shares = theme_shares(frame, pack)

    # The snapshot holds raw review text, so it stays in the git-ignored data folder.
    snapshot = data_dir / "snapshots" / f"{pack.name}-{run_date}.csv"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(snapshot, index=False)

    report = out_dir / f"{pack.name}-{run_date}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        render_battlecard(
            frame,
            shares,
            pack,
            run_date=run_date,
            listed=listed,
            empty_apps=empty_apps,
            tagger=tagger,
        )
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ariadne-pmm", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("packs", help="list the built-in research packs")

    sample = commands.add_parser(
        "sample", help="draw reviews from a run for hand labelling (accuracy check)"
    )
    sample.add_argument("snapshot", type=Path, help="a run's snapshot CSV in data/snapshots/")
    sample.add_argument("--n", type=int, default=100)
    sample.add_argument("--seed", type=int, default=7, help="same seed, same sample")
    sample.add_argument("--out", type=Path, default=Path("data/accuracy"))
    sample.add_argument("--pack", default="weakness_map", help="pack the run used")

    agree = commands.add_parser("agree", help="compare your labels with the tool's")
    agree.add_argument("sheet", type=Path, help="the labelled sheet from `sample`")
    agree.add_argument("--key", type=Path, help="the key from `sample` (default: next to sheet)")
    agree.add_argument("--pack", default="weakness_map")
    agree.add_argument("--out", type=Path, help="write the report here instead of printing it")

    compare = commands.add_parser("compare", help="compare two runs of the same pack")
    compare.add_argument("old", type=Path, help="the earlier run's snapshot CSV")
    compare.add_argument("new", type=Path, help="the later run's snapshot CSV")
    compare.add_argument("--pack", default="weakness_map")
    compare.add_argument("--out", type=Path, help="write the report here instead of printing it")

    discover = commands.add_parser("discover", help="find an app's competitors")
    discover.add_argument("seed", help="App Store ID or app name, e.g. 1459645446 or BeReal")
    discover.add_argument(
        "--keyword",
        action="append",
        default=[],
        help="extra search term for finding competitors (repeatable)",
    )
    discover.add_argument("--top", type=int, default=5)
    discover.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="drop an app from the competitors by ID or name (repeatable)",
    )
    discover.add_argument("--country", default="us")

    fetch = commands.add_parser("fetch", help="pull reviews and show counts, without labelling")
    _add_source_arguments(fetch)
    fetch.add_argument("--pack", default="weakness_map", help="pack to check sample sizes for")

    run = commands.add_parser("run", help="run a research pack")
    run.add_argument("pack", help="pack name or path to a pack YAML file")
    _add_source_arguments(run)
    run.add_argument("--reviews-file", type=Path, help="use reviews from a JSON file instead")
    run.add_argument(
        "--tagger",
        choices=["claude", "keywords"],
        default="claude",
        help="claude: most accurate, needs ANTHROPIC_API_KEY. keywords: free word rules",
    )
    run.add_argument("--model", default=DEFAULT_MODEL)
    run.add_argument("--out", type=Path, default=Path("reports"))
    return parser


def _add_source_arguments(command: argparse.ArgumentParser) -> None:
    """Options shared by every command that pulls reviews."""
    command.add_argument(
        "--app",
        action="append",
        type=parse_app,
        default=[],
        metavar="ID:NAME",
        help="App Store app to pull, e.g. 6759358792:'Shufl FM' (repeatable)",
    )
    command.add_argument("--seed", help="App Store ID or name: use it plus its top competitors")
    command.add_argument(
        "--keyword",
        action="append",
        default=[],
        help="extra search term for finding competitors (repeatable)",
    )
    command.add_argument("--top", type=int, default=5, help="competitors to add to --seed")
    command.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="drop an app from the competitors by ID or name (repeatable)",
    )
    command.add_argument("--country", default="us")
    command.add_argument("--pages", type=int, default=10, help="pages of 50 reviews per app")
    command.add_argument("--data", type=Path, default=Path("data"))


def _selected_apps(args: argparse.Namespace) -> list[tuple[str, str]]:
    apps = list(args.app)
    if args.seed:
        apps += discover_apps(args.seed, args.keyword, args.top, args.country, exclude=args.exclude)
    return list(dict.fromkeys(apps))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "packs":
        for name in available_packs():
            print(f"{name}: {load_pack(name).question}")
        return 0

    if args.command == "sample":
        snapshot = pd.read_csv(args.snapshot, dtype={"review_id": str})
        sheet, key = draw_sample(snapshot, n=args.n, seed=args.seed)
        args.out.mkdir(parents=True, exist_ok=True)
        sheet_path = args.out / f"{args.snapshot.stem}-sheet.csv"
        key_path = args.out / f"{args.snapshot.stem}-key.csv"
        sheet.to_csv(sheet_path, index=False)
        key.to_csv(key_path, index=False)
        themes = ", ".join(load_pack(args.pack).themes)
        print(f"Wrote {len(sheet)} reviews to {sheet_path}")
        print(f"Fill in human_theme with one of: {themes}")
        print(f"The tool's labels are in {key_path}. Don't open it until you're done.")
        return 0

    if args.command == "agree":
        key_path = args.key or args.sheet.with_name(args.sheet.name.replace("-sheet", "-key"))
        sheet = pd.read_csv(args.sheet, dtype={"review_id": str})
        key = pd.read_csv(key_path, dtype={"review_id": str})
        report = render_agreement(agreement(sheet, key, list(load_pack(args.pack).themes)))
        if args.out:
            args.out.write_text(report)
            print(f"Report written to {args.out}")
        else:
            print(report)
        return 0

    if args.command == "compare":
        old = pd.read_csv(args.old, dtype={"review_id": str})
        new = pd.read_csv(args.new, dtype={"review_id": str})
        diff = compare_runs(old, new, load_pack(args.pack))
        report = render_comparison(
            diff,
            args.old.stem,
            args.new.stem,
            only_old=sorted(set(old["app_name"]) - set(new["app_name"])),
            only_new=sorted(set(new["app_name"]) - set(old["app_name"])),
        )
        if args.out:
            args.out.write_text(report)
            print(f"Report written to {args.out}")
        else:
            print(report)
        return 0

    if args.command == "discover":
        discover_apps(args.seed, args.keyword, args.top, args.country, exclude=args.exclude)
        return 0

    reviews_file = getattr(args, "reviews_file", None)
    if not args.app and not args.seed and not reviews_file:
        print("Give a --seed app or at least one --app ID:NAME.", file=sys.stderr)
        return 2

    if args.command == "fetch":
        pulled = collect_reviews(_selected_apps(args), args.country, args.pages, args.data)
        print_sample_plan(pulled, load_pack(args.pack))
        return 0

    use_claude = args.tagger == "claude"
    if use_claude and not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "Set ANTHROPIC_API_KEY first (console.anthropic.com), "
            "or add --tagger keywords to label for free with word rules.",
            file=sys.stderr,
        )
        return 2

    if reviews_file:
        reviews = load_reviews_file(reviews_file)
    else:
        reviews = collect_reviews(_selected_apps(args), args.country, args.pages, args.data)

    client = None
    if use_claude:
        import anthropic  # imported here so the free paths work without the SDK configured

        client = anthropic.Anthropic()

    report = run_pack(
        args.pack, reviews, client, args.out, args.data, args.model, tagger=args.tagger
    )
    print(f"Report written to {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
