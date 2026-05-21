.PHONY: install test lint build-dataset demo clean

PY ?= python3
UV ?= uv

install:
	$(UV) venv --python 3.11 .venv || $(PY) -m venv .venv
	$(UV) pip install -e ".[dev]" || .venv/bin/pip install -e ".[dev]"

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check src tests

build-dataset:
	.venv/bin/python -m aig_harm_eval.cli build-dataset --out dist/dataset.v1.jsonl --stats dist/stats.md

demo:
	.venv/bin/python -m aig_harm_eval.cli demo --n 10

clean:
	rm -rf dist .venv .pytest_cache **/__pycache__
