"""Adapter base class: external dataset -> schema v1 items."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

from ..schema_validate import make_id, normalize_prompt, sha256_hash


class BaseAdapter(ABC):
    name: str = "base"
    version: str = "0.0.0"
    license: str = "CUSTOM"
    default_language: str = "en"
    source_url: str | None = None

    @abstractmethod
    def raw_records(self) -> Iterator[dict[str, Any]]:
        """Yield raw source records (anything)."""

    @abstractmethod
    def to_item(self, raw: dict[str, Any], idx: int) -> dict[str, Any] | None:
        """Convert one raw record to schema v1 item (or None to skip)."""

    def iter_items(self) -> Iterator[dict[str, Any]]:
        for i, r in enumerate(self.raw_records()):
            item = self.to_item(r, i)
            if item is None:
                continue
            self._finalize(item, i)
            yield item

    def _finalize(self, item: dict[str, Any], idx: int) -> None:
        prompt = item["prompt"]
        norm = normalize_prompt(prompt)
        item.setdefault("prompt_normalized", norm)
        item.setdefault("hash", sha256_hash(norm))
        item.setdefault("language", self.default_language)
        item.setdefault("license", self.license)
        item.setdefault(
            "source",
            {
                "name": self.name,
                "version": self.version,
                **({"url": self.source_url} if self.source_url else {}),
                "row_id": str(idx),
            },
        )
        item.setdefault("created_at", datetime.now(UTC).isoformat())
        item.setdefault("id", make_id(self.name, norm))
