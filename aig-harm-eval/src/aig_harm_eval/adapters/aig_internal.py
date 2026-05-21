"""Adapter for AI-Infra-Guard's bundled data/eval/*.json files."""
from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .base import BaseAdapter

# Mapping from upstream filename (without .json) -> schema v1 category
FILE_CATEGORY_MAP: dict[str, str] = {
    "cyberattack": "cyberattack",
    "copyright-violation": "copyright",
    "privacy-leakage": "privacy_pii",
    "misinformation": "misinformation",
    "violent": "violent",
    "non-violent-illegal-activity": "non_violent_illegal",
    "unethical-behavior": "unethical",
    "CBRN-weapon": "cbrn",
    "HarmfulEvalBenchmark": "custom",
    "JADE-db-v3.0": "custom",
    "ChatGPT-Jailbreak-Prompts": "jailbreak_generic",
    "JailBench-Tiny": "jailbreak_generic",
    "JailbreakPrompts-Tiny": "jailbreak_generic",
}

LANG_MAP = {"en": "en", "zh": "zh", "zh-en-mix": "mixed", "zh-tw": "zh-tw"}

# Categories the upstream dataset RESTRICTS (must be flagged)
RESTRICTED_CATEGORIES = {"cbrn", "minor_safety"}


class AIGInternalAdapter(BaseAdapter):
    name = "aig-internal"
    version = "2024.11"
    license = "CUSTOM"
    source_url = "https://github.com/Tencent/AI-Infra-Guard"

    def __init__(self, data_dir: Path | str, files: list[str] | None = None) -> None:
        self.data_dir = Path(data_dir)
        self.files = files or sorted(FILE_CATEGORY_MAP.keys())

    def raw_records(self) -> Iterator[dict[str, Any]]:
        for fname in self.files:
            fp = self.data_dir / f"{fname}.json"
            if not fp.exists():
                continue
            payload = json.loads(fp.read_text(encoding="utf-8"))
            file_lang = LANG_MAP.get(payload.get("language", "en"), "other")
            for row in payload.get("data", []):
                row = dict(row)
                row.setdefault("__file__", fname)
                row.setdefault("__file_lang__", file_lang)
                yield row

    def to_item(self, raw: dict[str, Any], idx: int) -> dict[str, Any] | None:
        prompt = raw.get("prompt")
        if not prompt or not isinstance(prompt, str):
            return None
        fname = raw["__file__"]
        category = FILE_CATEGORY_MAP.get(fname, "custom")
        item: dict[str, Any] = {
            "prompt": prompt,
            "category": category,
            "language": self._guess_lang(prompt, raw["__file_lang__"]),
            "source": {
                "name": self.name,
                "version": self.version,
                "url": self.source_url,
                "row_id": f"{fname}#{idx}",
            },
            "license": "RESTRICTED" if category in RESTRICTED_CATEGORIES else "CUSTOM",
            "attack_method": "raw",
            "tags": [f"file:{fname}"],
            "extra": {k: v for k, v in raw.items() if k not in {"prompt", "__file__", "__file_lang__"}},
        }
        # Map upstream's harmful_tag / attack_tag to sub_category / tags when present
        if raw.get("harmful_tag"):
            item["sub_category"] = str(raw["harmful_tag"])
        if raw.get("attack_tag"):
            item["tags"].append(f"attack:{raw['attack_tag']}")
        if raw.get("category"):
            item["tags"].append(f"upstream_cat:{raw['category']}")
        if category in RESTRICTED_CATEGORIES:
            item["compliance"] = {"reviewed": False, "notes": "auto-flagged RESTRICTED by category"}
        return item

    @staticmethod
    def _guess_lang(text: str, file_lang: str) -> str:
        if file_lang != "mixed":
            return file_lang
        # crude heuristic for mixed files
        n_cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        if n_cjk >= max(3, len(text) // 20):
            return "zh"
        return "en"
