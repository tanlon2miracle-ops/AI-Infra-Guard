#!/usr/bin/env python3
"""Monitor κ drift of the current judge ensemble vs a gold-labelled calibration set.

Inputs:
- --gold: JSONL of gold labels {item_id, label, severity}
- --judged: JSONL produced by `aig-eval judge` (current run)
- --baseline: optional previous κ snapshot JSON for drift Δ

Outputs:
- JSON to stdout with κ, severity Pearson r, per-category breakdown, drift flag
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path


def _kappa(a: list[str], b: list[str]) -> float:
    if not a:
        return 0.0
    labels = sorted(set(a) | set(b))
    n = len(a)
    obs = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    pa = {label: sum(1 for x in a if x == label) / n for label in labels}
    pb = {label: sum(1 for x in b if x == label) / n for label in labels}
    exp = sum(pa[label] * pb[label] for label in labels)
    return 1.0 if exp >= 1.0 else (obs - exp) / (1 - exp)


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return 0.0 if dx == 0 or dy == 0 else num / (dx * dy)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True, type=Path)
    ap.add_argument("--judged", required=True, type=Path)
    ap.add_argument("--baseline", type=Path)
    ap.add_argument("--alert-delta", type=float, default=0.05)
    args = ap.parse_args(argv)

    gold = {g["item_id"]: g for g in load_jsonl(args.gold)}
    judged = {j["item_id"]: j for j in load_jsonl(args.judged)}
    common = sorted(set(gold) & set(judged))
    if not common:
        print(json.dumps({"error": "no overlapping item_ids", "gold": len(gold), "judged": len(judged)}))
        return 2

    a_lbl, b_lbl = [], []
    a_sev, b_sev = [], []
    by_cat: dict[str, tuple[list[str], list[str]]] = defaultdict(lambda: ([], []))
    for k in common:
        g = gold[k]
        j = judged[k]
        a_lbl.append(g["label"])
        b_lbl.append(j.get("final_label") or j.get("label"))
        a_sev.append(float(g["severity"]))
        b_sev.append(float(j.get("final_severity") or j.get("severity", 0)))
        cat = g.get("category") or j.get("category", "unknown")
        by_cat[cat][0].append(g["label"])
        by_cat[cat][1].append(j.get("final_label") or j.get("label"))

    out = {
        "n": len(common),
        "kappa": round(_kappa(a_lbl, b_lbl), 4),
        "severity_pearson": round(_pearson(a_sev, b_sev), 4),
        "by_category": {c: {"n": len(v[0]), "kappa": round(_kappa(*v), 4)} for c, v in by_cat.items()},
    }

    if args.baseline and args.baseline.exists():
        prev = json.loads(args.baseline.read_text(encoding="utf-8"))
        delta = out["kappa"] - prev.get("kappa", 0)
        out["delta_kappa"] = round(delta, 4)
        out["alert"] = delta <= -args.alert_delta

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
