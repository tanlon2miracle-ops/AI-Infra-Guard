# Usage

## Install

```bash
cd aig-harm-eval
uv venv --python 3.11 .venv && uv pip install -e ".[dev]"
# or: python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"
```

## Test + lint

```bash
make test    # pytest
make lint    # ruff
```

## Build dataset

```bash
make build-dataset
# -> dist/dataset.v1.jsonl + dist/stats.md
```

Add HarmBench:
```bash
bash scripts/fetch_harmbench.sh
.venv/bin/python -m aig_harm_eval.cli build-dataset \
  --harmbench data_external/harmbench/harmbench_behaviors_text_all.csv
```

## Generate attack queries

```bash
.venv/bin/python -m aig_harm_eval.cli generate \
  --seed-file examples/seeds.jsonl \
  --out dist/generated.jsonl \
  --summary dist/generated_summary.json \
  --n 10
```

## Judge a response file

`responses.jsonl` lines: `{"item": <schema-v1 item>, "response": "<assistant text>"}`

```bash
.venv/bin/python -m aig_harm_eval.cli judge \
  --responses dist/responses.jsonl \
  --out dist/judged.jsonl \
  --judges mock,mock
```

Real LLM judges (require env):
```bash
export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=https://api.openai.com/v1
.venv/bin/python -m aig_harm_eval.cli judge \
  --responses dist/responses.jsonl --out dist/judged.jsonl \
  --judges 'llm:gpt-4o-mini,llm:gpt-4o@env=OPENAI_API_KEY'
```

## End-to-end run

```bash
.venv/bin/python -m aig_harm_eval.cli run \
  --dataset dist/dataset.v1.jsonl \
  --target mock \
  --judges mock,mock \
  --out-dir dist/run \
  --max-items 100
# -> dist/run/{responses,judged}.jsonl + abstain.csv + report.html
```

Against a real OpenAI-compatible endpoint:
```bash
export OPENAI_API_KEY=...
.venv/bin/python -m aig_harm_eval.cli run \
  --dataset dist/dataset.v1.jsonl \
  --target oai:gpt-4o-mini \
  --judges llm:gpt-4o-mini,llm:claude-3-5-sonnet@env=ANTHROPIC_API_KEY \
  --qps 2.0 --max-items 200
```

## One-shot demo

```bash
make demo
# -> dist/demo/report.html
```

## κ drift monitor

```bash
.venv/bin/python scripts/monitor_kappa.py \
  --gold dist/gold.jsonl --judged dist/judged.jsonl \
  --baseline dist/kappa_last_month.json
```
