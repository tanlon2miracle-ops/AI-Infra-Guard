"""End-to-end pipeline: dataset -> target -> dual-judge -> report.

Features:
- Streaming JSONL I/O
- Resume / checkpoint via processed_ids cache
- Per-call retry + backoff (delegated to target)
- Rate-limit pacing (--qps)
- HTML matrix report: category x attack_method x severity
"""
from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..judges import BaseJudge, ensemble, write_abstain_csv
from .target import BaseTarget

Triple = tuple[dict[str, Any], str]


@dataclass
class RunConfig:
    qps: float = 0.0  # 0 = no pacing
    max_items: int | None = None
    resume: bool = True


def _load_processed(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {json.loads(line)["item_id"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def iter_dataset(path: Path, limit: int | None = None) -> Iterator[dict[str, Any]]:
    n = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)
            n += 1
            if limit and n >= limit:
                return


def _pace(qps: float, last: float) -> float:
    if qps <= 0:
        return time.time()
    min_gap = 1.0 / qps
    now = time.time()
    wait = min_gap - (now - last)
    if wait > 0:
        time.sleep(wait)
    return time.time()


def run_eval(
    dataset_path: Path,
    target: BaseTarget,
    judges: list[BaseJudge],
    out_dir: Path,
    cfg: RunConfig,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    responses_path = out_dir / "responses.jsonl"
    judged_path = out_dir / "judged.jsonl"
    abstain_path = out_dir / "abstain.csv"
    report_path = out_dir / "report.html"

    processed = _load_processed(judged_path) if cfg.resume else set()
    n_done = 0
    n_err = 0
    last = 0.0
    triples: list[Triple] = []

    # streaming: target call + write response, then judge in batch at end
    with responses_path.open("a" if cfg.resume else "w", encoding="utf-8") as resp_f:
        for item in iter_dataset(dataset_path, cfg.max_items):
            if item["id"] in processed:
                continue
            try:
                last = _pace(cfg.qps, last)
                resp = target.respond(item["prompt"])
                resp_f.write(json.dumps({"item": item, "response": resp}, ensure_ascii=False) + "\n")
                triples.append((item, resp))
                n_done += 1
            except Exception as e:  # noqa: BLE001
                n_err += 1
                resp_f.write(json.dumps({"item": item, "error": str(e)}, ensure_ascii=False) + "\n")

    # judge all collected triples (skip ones already judged)
    new_results = ensemble(judges, triples)
    with judged_path.open("a" if cfg.resume else "w", encoding="utf-8") as jf:
        for r in new_results:
            jf.write(json.dumps({
                "item_id": r.item_id,
                "final_label": r.final_label,
                "final_severity": r.final_severity,
                "abstained": r.abstained,
                "verdicts": [v.to_dict() for v in r.verdicts],
            }, ensure_ascii=False) + "\n")
    n_abstain = write_abstain_csv(new_results, abstain_path)

    # build report (read all judged + dataset for context)
    report = build_report(dataset_path, judged_path)
    report_path.write_text(report, encoding="utf-8")
    return {
        "done": n_done,
        "errors": n_err,
        "abstain": n_abstain,
        "report": str(report_path),
        "judged": str(judged_path),
    }


def build_report(dataset_path: Path, judged_path: Path) -> str:
    items_by_id = {it["id"]: it for it in iter_dataset(dataset_path)}
    verdicts: list[dict[str, Any]] = []
    for line in judged_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            verdicts.append(json.loads(line))

    # matrix: category x attack_method -> Counter(severity)
    matrix: dict[tuple[str, str], Counter[int]] = defaultdict(Counter)
    label_counts: Counter[str] = Counter()
    cat_unsafe: Counter[str] = Counter()
    total = 0
    for v in verdicts:
        item = items_by_id.get(v["item_id"])
        if not item:
            continue
        total += 1
        cat = item["category"]
        am = item.get("attack_method", "raw")
        sev = v["final_severity"]
        matrix[(cat, am)][sev] += 1
        label_counts[v["final_label"]] += 1
        if v["final_label"] in {"partial_leak", "unsafe"}:
            cat_unsafe[cat] += 1

    return _render_html(matrix, label_counts, cat_unsafe, total)


def _render_html(
    matrix: dict[tuple[str, str], Counter[int]],
    label_counts: Counter[str],
    cat_unsafe: Counter[str],
    total: int,
) -> str:
    cats = sorted({c for c, _ in matrix.keys()})
    methods = sorted({m for _, m in matrix.keys()})
    rows = []
    for c in cats:
        cells = []
        for m in methods:
            sev_dist = matrix.get((c, m), Counter())
            total_cell = sum(sev_dist.values())
            if total_cell == 0:
                cells.append("<td>·</td>")
                continue
            mean_sev = sum(s * n for s, n in sev_dist.items()) / total_cell
            color = _heat(mean_sev)
            cells.append(
                f'<td style="background:{color};text-align:center" '
                f'title="severity dist: {dict(sev_dist)}">{total_cell}<br>'
                f'<small>μ={mean_sev:.1f}</small></td>'
            )
        rows.append(f"<tr><th>{c}</th>{''.join(cells)}</tr>")

    method_head = "".join(f"<th>{m}</th>" for m in methods)
    label_rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in label_counts.most_common())
    cat_rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in cat_unsafe.most_common())
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>AIG Harm-Eval Report</title>
<style>
body {{ font-family: -apple-system, sans-serif; margin: 20px; }}
table {{ border-collapse: collapse; margin: 12px 0; }}
th, td {{ border: 1px solid #ccc; padding: 6px 10px; }}
th {{ background: #f4f4f4; }}
h2 {{ margin-top: 24px; }}
</style></head><body>
<h1>AIG Harm-Eval Report</h1>
<p>Total judged: <b>{total}</b></p>
<h2>Label distribution</h2>
<table><tr><th>label</th><th>count</th></tr>{label_rows}</table>
<h2>Unsafe / partial_leak by category</h2>
<table><tr><th>category</th><th>count</th></tr>{cat_rows}</table>
<h2>Matrix: category × attack_method (cell = N, μ = mean severity)</h2>
<table><tr><th>category \\ method</th>{method_head}</tr>
{''.join(rows)}
</table>
</body></html>
"""


def _heat(severity: float) -> str:
    # 1 (green) -> 5 (red)
    s = max(1.0, min(5.0, severity))
    t = (s - 1) / 4
    r = int(80 + t * 175)
    g = int(200 - t * 160)
    return f"rgb({r},{g},80)"


def write_triples_for_judging(dataset: Iterable[dict[str, Any]], target: BaseTarget, out: Path) -> int:
    """Helper used by demo/CLI to materialize responses without judging."""
    n = 0
    with out.open("w", encoding="utf-8") as f:
        for item in dataset:
            try:
                resp = target.respond(item["prompt"])
            except Exception as e:  # noqa: BLE001
                resp = f"[ERROR: {e}]"
            f.write(json.dumps({"item": item, "response": resp}, ensure_ascii=False) + "\n")
            n += 1
    return n
