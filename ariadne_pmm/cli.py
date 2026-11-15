"""Command line entry point: run a research pack on a set of apps."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from ariadne_pmm.analyze.aggregate import build_frame, theme_shares
from ariadne_pmm.analyze.tagger import DEFAULT_MODEL, tag_reviews
from ariadne_pmm.ingest.app_store import fetch_reviews
from ariadne_pmm.ingest.discover import find_competitors, resolve_app, short_name
from ariadne_pmm.models import Review
from ariadne_pmm.pack import available_packs, load_pack
from ariadne_pmm.report import render_battlecard


def parse_app(value: str) -> tuple[str, str]:
    """Parse an --app value written as APP_ID:Name."""
    app_id, _, name = value.partition(":")
    if not app_id.strip().isdigit() or not name.strip():
        raise argparse.ArgumentTypeError(f"'{value}' should look like 6759358792:Shufl FM")
    return app_id.strip(), name.strip()


def discover_apps(
    seed_query: str, keywords: list[str], top: int, country: str, session=None
) -> list[tuple[str, str]]:
    """Resolve the seed app, find its competitors, print why each was picked.

    Returns the seed plus competitors as (app_id, name) pairs.
    """
    seed = resolve_app(seed_query, country=country, session=session)
    if seed is None:
        raise SystemExit(f"Could not find an App Store app matching '{seed_query}'.")

    print(f"Seed: {seed.name} (id {seed.app_id}, {seed.genre}, {seed.rating_count:,} ratings)")
    competitors = find_competitors(
        seed, keywords=keywords, top=top, country=country, session=session
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
        raw = data_dir / "raw" / f"{app_id}.json"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_text(json.dumps([r.to_dict() for r in pulled], indent=2))
        reviews.extend(pulled)
    return reviews


def load_reviews_file(path: Path) -> list[Review]:
    return [Review(**row) for row in json.loads(path.read_text())]


def run_pack(
    pack_name: str,
    reviews: list[Review],
    client,
    out_dir: Path,
    data_dir: Path,
    model: str = DEFAULT_MODEL,
    run_date: str | None = None,
) -> Path:
    """Tag, count and write the report. Returns the report path."""
    pack = load_pack(pack_name)
    run_date = run_date or datetime.now(tz=timezone.utc).date().isoformat()
    in_scope = [r for r in reviews if r.rating in pack.ratings]

    tags = tag_reviews(
        in_scope,
        pack,
        client,
        cache_path=data_dir / "cache" / f"{pack.cache_key}.jsonl",
        model=model,
    )
    frame = build_frame(in_scope, tags, pack)
    shares = theme_shares(frame, pack)

    # The snapshot holds raw review text, so it stays in the git-ignored data folder.
    snapshot = data_dir / "snapshots" / f"{pack.name}-{run_date}.csv"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(snapshot, index=False)

    report = out_dir / f"{pack.name}-{run_date}.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(render_battlecard(frame, shares, pack, run_date=run_date))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ariadne-pmm", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("packs", help="list the built-in research packs")

    discover = commands.add_parser("discover", help="find an app's competitors")
    discover.add_argument("seed", help="App Store ID or app name, e.g. 1459645446 or BeReal")
    discover.add_argument(
        "--keyword",
        action="append",
        default=[],
        help="extra search term for finding competitors (repeatable)",
    )
    discover.add_argument("--top", type=int, default=5)
    discover.add_argument("--country", default="us")

    fetch = commands.add_parser("fetch", help="pull reviews and show counts, without labelling")
    _add_source_arguments(fetch)

    run = commands.add_parser("run", help="run a research pack")
    run.add_argument("pack", help="pack name or path to a pack YAML file")
    _add_source_arguments(run)
    run.add_argument("--reviews-file", type=Path, help="use reviews from a JSON file instead")
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
    command.add_argument("--country", default="us")
    command.add_argument("--pages", type=int, default=10, help="pages of 50 reviews per app")
    command.add_argument("--data", type=Path, default=Path("data"))


def _selected_apps(args: argparse.Namespace) -> list[tuple[str, str]]:
    apps = list(args.app)
    if args.seed:
        apps += discover_apps(args.seed, args.keyword, args.top, args.country)
    return list(dict.fromkeys(apps))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "packs":
        for name in available_packs():
            print(f"{name}: {load_pack(name).question}")
        return 0

    if args.command == "discover":
        discover_apps(args.seed, args.keyword, args.top, args.country)
        return 0

    reviews_file = getattr(args, "reviews_file", None)
    if not args.app and not args.seed and not reviews_file:
        print("Give a --seed app or at least one --app ID:NAME.", file=sys.stderr)
        return 2

    if args.command == "fetch":
        collect_reviews(_selected_apps(args), args.country, args.pages, args.data)
        return 0

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY first (console.anthropic.com).", file=sys.stderr)
        return 2

    if reviews_file:
        reviews = load_reviews_file(reviews_file)
    else:
        reviews = collect_reviews(_selected_apps(args), args.country, args.pages, args.data)

    import anthropic  # imported here so listing packs works without the SDK configured

    report = run_pack(args.pack, reviews, anthropic.Anthropic(), args.out, args.data, args.model)
    print(f"Report written to {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
