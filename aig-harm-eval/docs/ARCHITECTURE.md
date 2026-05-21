# Architecture

```
              ┌──────────────────┐
              │ data/eval/*.json │  (upstream)
              │ HarmBench, ...   │
              └────────┬─────────┘
                       │
                ┌──────▼───────┐
                │  adapters/   │  -> schema v1 items
                └──────┬───────┘
                       │
                ┌──────▼───────┐
                │   dedup.py   │  exact(SHA-256) + near(MinHash)
                └──────┬───────┘
                       │
                ┌──────▼─────────────┐
                │ dist/dataset.v1.jsonl │
                └──────┬─────────────┘
                       │
        ┌──────────────┼────────────────┐
        │              │                │
 ┌──────▼─────┐  ┌─────▼──────┐  ┌──────▼────────┐
 │ generators │  │  target    │  │   judges      │
 │ seed_expand│  │ MockTarget │  │ MockJudge     │
 │ scorer     │  │ OAITarget  │  │ LLMJudge      │
 └──────┬─────┘  └─────┬──────┘  └──────┬────────┘
        │              │                │
        └──────────────▼────────────────┘
                       │
                ┌──────▼─────┐
                │ pipelines  │
                │ run_eval   │ -> responses.jsonl
                │            │ -> judged.jsonl
                │            │ -> abstain.csv
                │            │ -> report.html
                └────────────┘
```

## Modules

- `schema_validate.py` — load & cache JSON schema, normalize prompts, hash, make_id.
- `dedup.py` — first-seen wins; near-dups annotated via `near_dup_of`.
- `adapters/` — extend by subclassing `BaseAdapter`; `to_item` returns schema-v1 dict.
- `generators/seed_expander.py` — domain × difficulty × method expansion; optional `llm_fn`.
- `generators/scorer.py` — heuristic 3-axis scoring; swap to LLM later.
- `judges/` — rubric prompt (zh/en), Mock judge, OpenAI-compatible LLM judge, ensemble + Cohen's κ.
- `pipelines/` — streaming run with resume, QPS pacing, HTML matrix report.

## Extension points

| Need | Where |
|---|---|
| New dataset | `adapters/<name>.py` + register default in `build_dataset.default_adapters` |
| New attack method | `generators/seed_expander.py::ROLEPLAY_TEMPLATES` etc. |
| Real LLM judge | `judges/clients.py::LLMJudge` (provide env var) |
| New target | subclass `pipelines.BaseTarget` |
| Report layout | `pipelines/run_eval.py::_render_html` |

## Determinism

- `make_id` and hashing are deterministic.
- `MockJudge` and `MockTarget` accept seeds.
- `seed_expander` RNG is seeded per-seed (`f"{cfg.seed}:{seed.prompt}"`).
