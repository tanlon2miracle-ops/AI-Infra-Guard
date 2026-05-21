"""Schema validation for dataset items (v1)."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schema" / "dataset.schema.v1.json"

_ZERO_WIDTH = re.compile(r"[\u200B\u200C\u200D\uFEFF]")
_MULTISPACE = re.compile(r"\s+")


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _validator() -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(load_schema())


def normalize_prompt(text: str) -> str:
    """NFKC + strip zero-width + collapse whitespace + lowercase."""
    t = unicodedata.normalize("NFKC", text)
    t = _ZERO_WIDTH.sub("", t)
    t = _MULTISPACE.sub(" ", t).strip().lower()
    return t


def sha256_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_id(source_slug: str, prompt_norm: str) -> str:
    h12 = hashlib.sha1(prompt_norm.encode("utf-8")).hexdigest()[:12]
    slug = re.sub(r"[^a-z0-9_-]+", "-", source_slug.lower()).strip("-")
    if not slug:
        slug = "src"
    return f"{slug}-{h12}"


def validate_item(item: dict[str, Any]) -> list[str]:
    """Return list of validation error messages (empty if valid)."""
    errors = sorted(_validator().iter_errors(item), key=lambda e: e.path)
    return [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors]


def is_valid(item: dict[str, Any]) -> bool:
    return not validate_item(item)
