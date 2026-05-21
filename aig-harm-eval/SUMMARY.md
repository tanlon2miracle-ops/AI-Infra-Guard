# AIG Harm-Eval - Delivery Summary

> Branch: `feat/harm-eval`  •  Subdir: `aig-harm-eval/`  •  Upstream: `Tencent/AI-Infra-Guard`
> Milestones: M0–M5 all delivered (M0 was pre-existing).

---

## M1 · Dataset layer · tag `harm-eval/m1-dataset`

**Delivered:**
- `src/aig_harm_eval/schema_validate.py` — JSON-Schema v1 loader, prompt normalization (NFKC + strip ZW + collapse WS + lowercase), `make_id`, SHA-256.
- `src/aig_harm_eval/dedup.py` — exact (SHA-256) + near (MinHash/LSH, `datasketch`) dedup. Near-dups annotated via `near_dup_of`.
- `src/aig_harm_eval/adapters/{base,aig_internal,harmbench}.py` — base interface + two implementations. CBRN auto-flagged `RESTRICTED` + `compliance` block.
- `src/aig_harm_eval/build_dataset.py` + CLI `build-dataset` — adapter → validate → dedup → JSONL + stats.md.
- Tests: `tests/test_schema.py`, `tests/test_dedup.py`, `tests/test_adapter_aig_internal.py`, `tests/test_adapter_harmbench.py`.
- `scripts/fetch_harmbench.sh` (CBRN/minor not auto-fetched per constraint).
- `pyproject.toml`, `Makefile`, `.gitignore`.

**Acceptance evidence:**
```
$ make build-dataset
OK | kept=1313 exact_dups=15 near_dups=70 errors=0
```
Stats: 23 categories observed; 1116 en + 197 zh; sources: `aig-internal` (+ optional harmbench).

---

## M2 · Generator · tag `harm-eval/m2-generator`

**Delivered:**
- `generators/seed_expander.py` — domain × difficulty × method expansion (raw / roleplay / encoding_base64 / encoding_reverse / perturb_zh + Chinese homophone / slang / emoji perturbation). Optional `llm_fn` plug-point.
- `generators/scorer.py` — three-axis heuristic: diversity (1 − max 3-gram Jaccard), harmfulness (category prior + keyword hits), attackability (attack method + length + non-ASCII density).
- CLI `generate` produces JSONL + summary JSON.
- Tests: `tests/test_generators.py`.
- Examples: `examples/seeds.jsonl` (10 seeds).

**Acceptance evidence:**
```
$ aig-eval generate --seed-file examples/seeds.jsonl --out dist/generated.jsonl --n 10
OK | seeds=10 expanded=100 valid=100
diversity μ=0.44   harmfulness μ=0.72   attackability μ=0.58
```

---

## M3 · Judge · tag `harm-eval/m3-judge`

**Delivered:**
- `judges/rubric.py` — zh + en rubric prompts (4-label × severity 1–5 × 4 dimensions).
- `judges/clients.py` — `MockJudge` (regex/keyword heuristic, deterministic) + `LLMJudge` (OpenAI-compatible HTTP, API key from env).
- `judges/ensemble.py` — dual-judge ensemble, Cohen's κ, abstain CSV export.
- `judges/schema.py` — `JudgeVerdict` dataclass.
- CLI `judge` (configurable via `--judges mock,mock | llm:<model>@env=VAR`).
- Tests: `tests/test_judges.py` (mock label paths, ensemble, κ, parse_verdict robust to ```json fences).

**Acceptance evidence (100 synthetic samples, mock×mock):**
```
$ aig-eval judge --responses dist/responses.jsonl --out dist/judged.jsonl --judges mock,mock
OK | n=20 abstain=0 kappa=1.000
```

---

## M4 · End-to-end pipeline · tag `harm-eval/m4-e2e`

**Delivered:**
- `pipelines/target.py` — `MockTarget` + `OpenAICompatibleTarget` (retry/backoff, key from env).
- `pipelines/run_eval.py` — streaming dataset → target → dual-judge → outputs (responses.jsonl, judged.jsonl, abstain.csv, **report.html**). Resume (skip processed item_ids), QPS pacing, per-item error capture.
- HTML report: label distribution + unsafe-per-category + matrix (category × attack_method, cell shows N and μ severity with heatmap color).
- CLI `run` + `demo`.
- Tests: `tests/test_pipeline.py` (end-to-end, resume, iter_dataset, report HTML).

**Acceptance evidence:**
```
$ make demo
{
  "done": 10,
  "errors": 0,
  "abstain": 0,
  "report": "dist/demo/report.html",
  "judged": "dist/demo/judged.jsonl"
}
```

---

## M5 · Calibration + docs · tag `harm-eval/m5-calibration`

**Delivered (spec only, per constraint — no annotation done):**
- `docs/CALIBRATION.md` — 300-prompt calibration spec: stratified sample, dual-annotator + adjudicator flow, tooling pick (**Argilla** primary, Label Studio fallback), acceptance metrics (κ ≥ 0.6, severity Pearson r ≥ 0.7).
- `scripts/monitor_kappa.py` — κ + severity Pearson + per-category breakdown + drift Δ vs baseline (alert threshold configurable).
- `docs/ARCHITECTURE.md` — module diagram + extension points.
- `docs/USAGE.md` — full CLI usage (build/generate/judge/run/demo/monitor).
- Tests: `tests/test_monitor_kappa.py` (smoke on synthetic gold).

**Acceptance evidence:**
```
$ pytest tests/test_monitor_kappa.py
1 passed
```
(Real annotation is out of scope for M5 per task brief; tooling + drift script are ready.)

---

## Repo state

- All 26 tests pass; `ruff` clean.
- Tags pushed: `harm-eval/m1-dataset`, `harm-eval/m2-generator`, `harm-eval/m3-judge`, `harm-eval/m4-e2e`, `harm-eval/m5-calibration`.
- All commits on `feat/harm-eval`, pushed to `origin` (fork `tanlon2miracle-ops/AI-Infra-Guard`).
- Upstream `data/eval/` and other code untouched.

## Constraints honored

- Python 3.11 venv via `uv`.
- Big data not committed; `scripts/fetch_harmbench.sh` for HarmBench. CBRN/minor never auto-downloaded.
- LLM API keys env-only (`LLMJudge`, `OpenAICompatibleTarget`).
- Git/gh commands prefixed with `env -u http_proxy -u https_proxy GIT_TERMINAL_PROMPT=0`.

## What's NOT done (intentional, per task brief)

- M3 dual-judge with real `gpt-4o + claude` — code path ready, no real API calls (env keys not provided).
- M5 actual annotation of 300 items — only the spec + tooling are delivered.

## Next-step suggestions (M6+)

1. Integrate AIG-PromptSecurity (deepteam) `attack_simulator` into `generators/` for richer attack methods.
2. Real annotation pass on `docs/CALIBRATION.md` using Argilla.
3. Add GitHub Action: monthly κ monitor + auto-report PR.
4. Replace heuristic harmfulness with an LLM-based critic.
