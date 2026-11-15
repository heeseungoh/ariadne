"""Label each review with one theme from the pack's fixed list, using Claude.

Claude only reads and labels. It never counts: all numbers are computed in
aggregate.py from these labels. Two guards keep the labels honest:

- a theme outside the pack's list is replaced with "other"
- a quote that is not word-for-word in the review is discarded
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from positioning_lab.models import Review
from positioning_lab.pack import FALLBACK_THEME, Pack

DEFAULT_MODEL = "claude-haiku-5-5"
BATCH_SIZE = 20

SYSTEM_PROMPT = """You label customer reviews for a product marketing team.

For each review, pick the ONE theme that best describes the reviewer's main complaint.
Use only these theme keys:

{themes}

Also copy the single most telling sentence or phrase from the review as "quote".
The quote must be copied word for word from the review text. Do not paraphrase.

Reply with a JSON array only, one object per review, in this shape:
[{{"id": "<review id>", "theme": "<theme key>", "quote": "<verbatim quote>"}}]"""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _build_prompt(reviews: list[Review]) -> str:
    blocks = [
        f'<review id="{r.review_id}" rating="{r.rating}">\n{r.title}\n{r.text}\n</review>'
        for r in reviews
    ]
    return "Label these reviews:\n\n" + "\n\n".join(blocks)


def _parse_reply(reply: str) -> list[dict]:
    start, end = reply.find("["), reply.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        parsed = json.loads(reply[start : end + 1])
    except json.JSONDecodeError:
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _validate(item: dict, review: Review, pack: Pack) -> dict:
    theme = str(item.get("theme", "")).strip()
    if theme not in pack.themes:
        theme = FALLBACK_THEME

    quote = str(item.get("quote", "")).strip()
    source = _normalize(f"{review.title} {review.text}")
    if not quote or _normalize(quote) not in source:
        quote = ""

    return {"review_id": review.review_id, "theme": theme, "quote": quote}


def load_cache(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    rows = (json.loads(line) for line in path.read_text().splitlines() if line.strip())
    return {row["review_id"]: row for row in rows}


def tag_reviews(
    reviews: list[Review],
    pack: Pack,
    client,
    cache_path: Path | None = None,
    model: str = DEFAULT_MODEL,
    batch_size: int = BATCH_SIZE,
) -> dict[str, dict]:
    """Return {review_id: {"review_id", "theme", "quote"}} for every review.

    Reviews already in the cache are not sent again, so reruns cost nothing
    and give the same labels.
    """
    tags = load_cache(cache_path) if cache_path else {}
    todo = [r for r in reviews if r.review_id not in tags]
    system = SYSTEM_PROMPT.format(
        themes="\n".join(f"- {key}: {desc}" for key, desc in pack.themes.items())
    )

    for i in range(0, len(todo), batch_size):
        batch = todo[i : i + batch_size]
        response = client.messages.create(
            model=model,
            max_tokens=4000,
            system=system,
            messages=[{"role": "user", "content": _build_prompt(batch)}],
        )
        by_id = {str(item.get("id")): item for item in _parse_reply(response.content[0].text)}

        new_rows = []
        for review in batch:
            row = _validate(by_id.get(review.review_id, {}), review, pack)
            tags[review.review_id] = row
            new_rows.append(row)

        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with cache_path.open("a") as handle:
                for row in new_rows:
                    handle.write(json.dumps(row) + "\n")

    return {r.review_id: tags[r.review_id] for r in reviews}
