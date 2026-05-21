"""Build a unified dataset.v1.jsonl from configured adapters."""
from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .adapters import AIGInternalAdapter, BaseAdapter, HarmBenchAdapter
from .dedup import DedupResult, dedup
from .schema_validate import validate_item

REPO_ROOT = Path(__file__).resolve().parents[3]  # AI-Infra-Guard root
DEFAULT_AIG_DATA = REPO_ROOT / "data" / "eval"


def default_adapters(harmbench_path: Path | None = None) -> list[BaseAdapter]:
    adapters: list[BaseAdapter] = [AIGInternalAdapter(DEFAULT_AIG_DATA)]
    if harmbench_path and Path(harmbench_path).exists():
        adapters.append(HarmBenchAdapter(harmbench_path))
    return adapters


def collect(adapters: Iterable[BaseAdapter]) -> tuple[list[dict[str, Any]], list[str]]:
    items: list[dict[str, Any]] = []
    errors: list[str] = []
    for ad in adapters:
        for it in ad.iter_items():
            errs = validate_item(it)
            if errs:
                errors.append(f"[{ad.name}#{it.get('id','?')}] " + "; ".join(errs))
                continue
            items.append(it)
    return items, errors


def write_jsonl(items: Iterable[dict[str, Any]], out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
            n += 1
    return n


def render_stats(items: list[dict[str, Any]], dedup_res: DedupResult, errors: list[str]) -> str:
    by_cat = Counter(i["category"] for i in items)
    by_src = Counter(i["source"]["name"] for i in items)
    by_lang = Counter(i["language"] for i in items)
    by_lic = Counter(i["license"] for i in items)
    lines = [
        "# Dataset v1 Stats",
        "",
        f"- Total kept: **{len(items)}**",
        f"- Exact duplicates dropped: {dedup_res.exact_dups}",
        f"- Near duplicates dropped: {dedup_res.near_dups}",
        f"- Validation errors: {len(errors)}",
        "",
        "## By category",
        "",
        "| category | count |",
        "|---|---|",
    ]
    lines += [f"| {k} | {v} |" for k, v in by_cat.most_common()]
    lines += ["", "## By source", "", "| source | count |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in by_src.most_common()]
    lines += ["", "## By language", "", "| language | count |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in by_lang.most_common()]
    lines += ["", "## By license", "", "| license | count |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in by_lic.most_common()]
    if errors:
        lines += ["", "## Validation errors (first 20)", ""]
        lines += [f"- {e}" for e in errors[:20]]
    return "\n".join(lines) + "\n"


def build(
    out_path: Path,
    stats_path: Path,
    harmbench_path: Path | None = None,
    near_threshold: float = 0.85,
) -> dict[str, Any]:
    adapters = default_adapters(harmbench_path)
    raw_items, errors = collect(adapters)
    res = dedup(raw_items, near_threshold=near_threshold)
    n = write_jsonl(res.kept, out_path)
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(render_stats(res.kept, res, errors), encoding="utf-8")
    return {
        "kept": n,
        "exact_dups": res.exact_dups,
        "near_dups": res.near_dups,
        "errors": len(errors),
    }
