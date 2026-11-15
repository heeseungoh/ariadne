"""Shared data model."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Review:
    """One customer review. Author names are deliberately never stored."""

    review_id: str
    app_id: str
    app_name: str
    rating: int
    title: str
    text: str
    version: str
    date: str
    source: str = "app_store"

    def to_dict(self) -> dict:
        return asdict(self)
