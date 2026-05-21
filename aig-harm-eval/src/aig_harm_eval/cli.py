"""CLI entry-point for aig-eval."""
from __future__ import annotations

from pathlib import Path

import click

from .build_dataset import build


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


if __name__ == "__main__":
    main()
