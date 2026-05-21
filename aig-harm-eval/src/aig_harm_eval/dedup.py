"""Exact (SHA-256) + near-duplicate (MinHash) deduplication."""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Any

from datasketch import MinHash, MinHashLSH


def _shingles(text: str, k: int = 5) -> set[str]:
    text = text.replace(" ", "")
    if len(text) <= k:
        return {text}
    return {text[i : i + k] for i in range(len(text) - k + 1)}


def minhash(text: str, num_perm: int = 128) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for sh in _shingles(text):
        m.update(sh.encode("utf-8"))
    return m


@dataclass
class DedupResult:
    kept: list[dict[str, Any]]
    exact_dups: int
    near_dups: int


def dedup(
    items: Iterable[dict[str, Any]],
    near_threshold: float = 0.85,
    num_perm: int = 128,
) -> DedupResult:
    """Exact dedup by `hash` field; near-dup by MinHash on prompt_normalized.

    First-seen wins. Near-duplicates are dropped, but their id is appended to the
    kept entry's `near_dup_of`.
    """
    seen_hash: dict[str, dict[str, Any]] = {}
    lsh = MinHashLSH(threshold=near_threshold, num_perm=num_perm)
    mh_cache: dict[str, MinHash] = {}
    kept: list[dict[str, Any]] = []
    exact = 0
    near = 0

    for it in items:
        h = it.get("hash")
        if not h:
            continue
        if h in seen_hash:
            exact += 1
            continue
        norm = it.get("prompt_normalized") or it.get("prompt", "")
        mh = minhash(norm, num_perm=num_perm)
        dups = lsh.query(mh)
        if dups:
            near += 1
            owner_id = dups[0]
            owner = seen_hash[owner_id]
            owner.setdefault("near_dup_of", []).append(it["id"])
            continue
        seen_hash[h] = it
        mh_cache[h] = mh
        lsh.insert(h, mh)
        kept.append(it)

    return DedupResult(kept=kept, exact_dups=exact, near_dups=near)


def iter_jsonl(path) -> Iterator[dict[str, Any]]:
    import json

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)
