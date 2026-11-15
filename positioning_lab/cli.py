"""Command line entry point: run a research pack on a set of apps."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from positioning_lab.analyze.aggregate import build_frame, theme_shares
from positioning_lab.analyze.tagger import DEFAULT_MODEL, tag_reviews
from positioning_lab.ingest.app_store import fetch_reviews
from positioning_lab.models import Review
from positioning_lab.pack import available_packs, load_pack
from positioning_lab.report import render_battlecard


def parse_app(value: str) -> tuple[str, str]:
    """Parse an --app value written as APP_ID:Name."""
    app_id, _, name = value.partition(":")
    if not app_id.strip().isdigit() or not name.strip():
        raise argparse.ArgumentTypeError(f"'{value}' should look like 6759358792:Shufl FM")
    return app_id.strip(), name.strip()


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
    parser = argparse.ArgumentParser(prog="positioning-lab", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("packs", help="list the built-in research packs")

    run = commands.add_parser("run", help="run a research pack")
    run.add_argument("pack", help="pack name or path to a pack YAML file")
    run.add_argument(
        "--app",
        action="append",
        type=parse_app,
        default=[],
        metavar="ID:NAME",
        help="App Store app to pull, e.g. 6759358792:'Shufl FM' (repeatable)",
    )
    run.add_argument("--reviews-file", type=Path, help="use reviews from a JSON file instead")
    run.add_argument("--country", default="us")
    run.add_argument("--pages", type=int, default=10, help="pages of 50 reviews per app (max 10)")
    run.add_argument("--model", default=DEFAULT_MODEL)
    run.add_argument("--out", type=Path, default=Path("reports"))
    run.add_argument("--data", type=Path, default=Path("data"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "packs":
        for name in available_packs():
            print(f"{name}: {load_pack(name).question}")
        return 0

    if not args.app and not args.reviews_file:
        print("Give at least one --app ID:NAME or a --reviews-file.", file=sys.stderr)
        return 2
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY first (console.anthropic.com).", file=sys.stderr)
        return 2

    if args.reviews_file:
        reviews = load_reviews_file(args.reviews_file)
    else:
        reviews = []
        for app_id, name in args.app:
            pulled = fetch_reviews(app_id, name, country=args.country, pages=args.pages)
            print(f"{name}: pulled {len(pulled)} reviews")
            raw = args.data / "raw" / f"{app_id}.json"
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_text(json.dumps([r.to_dict() for r in pulled], indent=2))
            reviews.extend(pulled)

    import anthropic  # imported here so listing packs works without the SDK configured

    report = run_pack(args.pack, reviews, anthropic.Anthropic(), args.out, args.data, args.model)
    print(f"Report written to {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
