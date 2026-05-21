"""Adapter for HarmBench behaviors_text CSV/JSONL.

HarmBench license: MIT. Schema reference:
https://github.com/centerforaisafety/HarmBench

Expected input: a TSV/CSV with columns including `Behavior` (or `prompt`) and optionally
`SemanticCategory`, `FunctionalCategory`. We accept either CSV or JSONL.
"""
from __future__ import annotations

import csv
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .base import BaseAdapter

# HarmBench semantic categories -> schema v1 category
SEMANTIC_MAP: dict[str, str] = {
    "cybercrime_intrusion": "cyberattack",
    "chemical_biological": "cbrn",
    "harmful": "unethical",
    "harassment_bullying": "toxicity",
    "illegal": "illegal_activity",
    "misinformation_disinformation": "misinformation",
    "copyright": "copyright",
    "privacy": "privacy_pii",
}


class HarmBenchAdapter(BaseAdapter):
    name = "harmbench"
    version = "2024-02"
    license = "MIT"
    default_language = "en"
    source_url = "https://github.com/centerforaisafety/HarmBench"

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def raw_records(self) -> Iterator[dict[str, Any]]:
        if not self.path.exists():
            return
        suffix = self.path.suffix.lower()
        if suffix in {".jsonl", ".ndjson"}:
            with self.path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        yield json.loads(line)
        elif suffix in {".csv", ".tsv"}:
            delim = "\t" if suffix == ".tsv" else ","
            with self.path.open(encoding="utf-8", newline="") as f:
                yield from csv.DictReader(f, delimiter=delim)
        else:
            raise ValueError(f"Unsupported HarmBench file: {self.path}")

    def to_item(self, raw: dict[str, Any], idx: int) -> dict[str, Any] | None:
        prompt = raw.get("Behavior") or raw.get("behavior") or raw.get("prompt")
        if not prompt:
            return None
        semantic = (raw.get("SemanticCategory") or raw.get("semantic_category") or "").lower()
        functional = (raw.get("FunctionalCategory") or raw.get("functional_category") or "").lower()
        category = SEMANTIC_MAP.get(semantic, "custom")
        row_id = raw.get("BehaviorID") or raw.get("id") or str(idx)
        item: dict[str, Any] = {
            "prompt": prompt,
            "category": category,
            "sub_category": semantic or None,
            "language": "en",
            "source": {
                "name": self.name,
                "version": self.version,
                "url": self.source_url,
                "row_id": str(row_id),
            },
            "license": "MIT" if category != "cbrn" else "RESTRICTED",
            "attack_method": "raw",
            "tags": [t for t in [f"functional:{functional}" if functional else None] if t],
            "extra": {k: v for k, v in raw.items() if k not in {"Behavior", "behavior", "prompt"}},
        }
        if category == "cbrn":
            item["compliance"] = {"reviewed": False, "notes": "CBRN auto-flagged RESTRICTED"}
        # remove None sub_category
        if not item.get("sub_category"):
            item.pop("sub_category", None)
        return item
