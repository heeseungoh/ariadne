"""Research packs: one PMM question with a fixed, repeatable recipe."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

PACK_DIR = Path(__file__).parent / "packs"
FALLBACK_THEME = "other"


@dataclass(frozen=True)
class Pack:
    name: str
    version: int
    question: str
    deliverable: str
    ratings: tuple[int, ...]
    min_reviews: int
    min_sample: int
    themes: dict[str, str]
    keywords: dict[str, tuple[str, ...]] = field(default_factory=dict)
    title: str = "Research report"
    subject: str = "reviews"
    focus: str = "main point"

    def sample_tier(self, n: int) -> str:
        """How much an app's sample of n reviews can support: none, list, counts or full."""
        if n <= 0:
            return "none"
        if n < self.min_reviews:
            return "list"
        if n < self.min_sample:
            return "counts"
        return "full"

    @property
    def cache_key(self) -> str:
        """Changes whenever the pack's theme list changes, so old tags are not reused."""
        return f"{self.name}-v{self.version}"


def available_packs() -> list[str]:
    return sorted(path.stem for path in PACK_DIR.glob("*.yaml"))


def load_pack(name_or_path: str) -> Pack:
    """Load a built-in pack by name, or any pack from a YAML file path."""
    path = Path(name_or_path)
    if not path.suffix:
        path = PACK_DIR / f"{name_or_path}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"No pack '{name_or_path}'. Built-in packs: {', '.join(available_packs())}"
        )

    raw = yaml.safe_load(path.read_text())
    themes = dict(raw.get("themes") or {})
    if FALLBACK_THEME not in themes:
        raise ValueError(f"Pack '{raw.get('name')}' must define an '{FALLBACK_THEME}' theme")

    ratings = tuple(int(r) for r in raw.get("ratings", [1, 2, 3, 4, 5]))
    if not ratings or any(r < 1 or r > 5 for r in ratings):
        raise ValueError("Pack ratings must be between 1 and 5")

    keywords = {
        theme: tuple(str(word).lower() for word in words)
        for theme, words in (raw.get("keywords") or {}).items()
    }
    unknown = sorted(set(keywords) - set(themes))
    if unknown:
        raise ValueError(f"Pack keywords name themes that do not exist: {', '.join(unknown)}")

    return Pack(
        name=raw["name"],
        version=int(raw.get("version", 1)),
        question=raw["question"],
        deliverable=raw.get("deliverable", "report"),
        ratings=ratings,
        min_reviews=int(raw.get("min_reviews", 10)),
        min_sample=int(raw.get("min_sample", 30)),
        themes=themes,
        keywords=keywords,
        title=str(raw.get("title", raw["name"].replace("_", " ").capitalize())),
        subject=str(raw.get("subject", "reviews")),
        focus=str(raw.get("focus", "main point")),
    )
