"""CLI entry-point for aig-eval."""
from __future__ import annotations

import json
from pathlib import Path

import click

from .build_dataset import build
from .generators import ExpandConfig, expand_seeds, load_seeds_jsonl, score_items, summarize
from .schema_validate import validate_item


@click.group()
def main() -> None:
    """aig-eval: harm-evaluation toolkit."""


@main.command("build-dataset")
@click.option("--out", "out_path", default="dist/dataset.v1.jsonl", type=click.Path())
@click.option("--stats", "stats_path", default="dist/stats.md", type=click.Path())
@click.option("--harmbench", "harmbench_path", default=None, type=click.Path(exists=False))
@click.option("--near-threshold", default=0.85, type=float)
def build_dataset(out_path: str, stats_path: str, harmbench_path: str | None, near_threshold: float) -> None:
    """Build unified dataset.v1.jsonl from configured adapters."""
    result = build(
        out_path=Path(out_path),
        stats_path=Path(stats_path),
        harmbench_path=Path(harmbench_path) if harmbench_path else None,
        near_threshold=near_threshold,
    )
    click.echo(f"OK | kept={result['kept']} exact_dups={result['exact_dups']} "
               f"near_dups={result['near_dups']} errors={result['errors']}")
    click.echo(f"wrote: {out_path}")
    click.echo(f"stats: {stats_path}")


@main.command("generate")
@click.option("--seed-file", required=True, type=click.Path(exists=True))
@click.option("--out", "out_path", required=True, type=click.Path())
@click.option("--n", "n_per_seed", default=5, type=int, help="variants per seed")
@click.option("--summary", "summary_path", default=None, type=click.Path())
def generate(seed_file: str, out_path: str, n_per_seed: int, summary_path: str | None) -> None:
    """Expand a seed JSONL file into N attack queries with three-axis scores."""
    from pathlib import Path

    seeds = load_seeds_jsonl(seed_file)
    cfg = ExpandConfig(n_per_seed=n_per_seed)
    items = expand_seeds(seeds, cfg)
    items = score_items(items)
    # validation: drop invalid ones
    valid: list[dict] = []
    for it in items:
        if not validate_item(it):
            valid.append(it)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for it in valid:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    s = summarize(valid)
    if summary_path:
        Path(summary_path).write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
    click.echo(f"OK | seeds={len(seeds)} expanded={len(items)} valid={len(valid)}")
    click.echo(json.dumps(s, ensure_ascii=False))


@main.command("judge")
@click.option("--responses", "resp_path", required=True, type=click.Path(exists=True),
              help="JSONL with {item: {...}, response: str} per line")
@click.option("--out", "out_path", required=True, type=click.Path())
@click.option("--abstain", "abstain_path", default="dist/abstain.csv", type=click.Path())
@click.option("--judges", "judges_spec", default="mock,mock",
              help="comma-separated: mock | llm:<model>[@env=VAR]")
def judge_cmd(resp_path: str, out_path: str, abstain_path: str, judges_spec: str) -> None:
    """Run dual-judge ensemble on a response JSONL."""
    from pathlib import Path

    from .judges import LLMJudge, MockJudge, cohen_kappa, ensemble, write_abstain_csv

    def _build(spec: str):
        spec = spec.strip()
        if spec == "mock":
            return MockJudge()
        if spec.startswith("llm:"):
            rest = spec[4:]
            model, _, env = rest.partition("@env=")
            return LLMJudge(model=model, api_key_env=env or "OPENAI_API_KEY")
        raise click.BadParameter(f"unknown judge spec: {spec}")

    parts = [s for s in judges_spec.split(",") if s.strip()]
    if len(parts) < 2:
        raise click.BadParameter("need >=2 judges; e.g. --judges mock,mock")
    # disambiguate two mocks with judge_id suffix
    judges_list = [_build(p) for p in parts]
    if all(isinstance(j, MockJudge) for j in judges_list):
        for i, j in enumerate(judges_list):
            j.judge_id = f"mock-v1#{i}"

    triples = []
    for line in Path(resp_path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        triples.append((d["item"], d.get("response", "")))

    results = ensemble(judges_list, triples)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps({
                "item_id": r.item_id,
                "final_label": r.final_label,
                "final_severity": r.final_severity,
                "abstained": r.abstained,
                "verdicts": [v.to_dict() for v in r.verdicts],
            }, ensure_ascii=False) + "\n")
    n_abs = write_abstain_csv(results, Path(abstain_path))
    kappa = cohen_kappa([r.verdicts[0] for r in results], [r.verdicts[1] for r in results])
    click.echo(f"OK | n={len(results)} abstain={n_abs} kappa={kappa:.3f}")


if __name__ == "__main__":
    main()
