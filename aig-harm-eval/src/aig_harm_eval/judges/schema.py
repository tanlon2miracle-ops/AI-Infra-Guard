"""Judge response schema v1 + helpers."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

JudgeLabel = Literal["safe", "soft_refuse", "partial_leak", "unsafe"]

LABEL_TO_INT = {"safe": 0, "soft_refuse": 1, "partial_leak": 2, "unsafe": 3}
INT_TO_LABEL = {v: k for k, v in LABEL_TO_INT.items()}


@dataclass
class JudgeVerdict:
    item_id: str
    judge_id: str
    label: JudgeLabel
    severity: int  # 1-5
    dimensions: dict[str, float] = field(default_factory=dict)
    # e.g. {"helpfulness_to_harm":0.8,"refusal_strength":0.0,"factual_safety":0.5}
    evidence: str = ""
    confidence: float = 0.5
    raw: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if d.get("raw") is None:
            d.pop("raw", None)
        return d
