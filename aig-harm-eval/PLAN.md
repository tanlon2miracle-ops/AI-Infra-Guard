# PLAN - AIG Harm-Eval Extension

> 目标：在 fork 的 AI-Infra-Guard 上，搭建独立子项目 `aig-harm-eval`，专注"大模型攻击 + 回复安全评测"三件套。
> 上游：Tencent/AI-Infra-Guard  
> Fork：tanlon2miracle-ops/AI-Infra-Guard  
> 工作分支：`feat/harm-eval`  
> 子目录：`aig-harm-eval/`（不动上游代码，便于 rebase）

---

## 里程碑（每个完成后 commit + tag + push）

### M0 · 仓库初始化  ✅ tag: `harm-eval/m0-init`
- 切 `feat/harm-eval` 分支
- 建 `aig-harm-eval/` 子目录骨架
- 落地 RESEARCH.md + schema v1
- 写 README + LICENSE 引用
- **验收**：分支 push，能在 GitHub 看到结构

### M1 · 数据集层 MVP  → tag: `harm-eval/m1-dataset`
1. 实现 schema 校验器 `schema/validate.py`（jsonschema）
2. 写 adapter 接口 + 2 个实现：
   - `adapters/aig_internal.py`（吃现有 `data/eval/*.json`）
   - `adapters/harmbench.py`（HarmBench behaviors_text）
3. 实现 `dedup.py`：SHA-256 精确 + MinHash 近似 (datasketch)
4. 构建脚本 `build_dataset.py`：跑 adapter → 校验 → 去重 → 输出 `dist/dataset.v1.jsonl` + `dist/stats.md`
5. CI: `make test` 跑 schema 校验 + adapter 单测
- **验收**：能跑通 `make build-dataset`，输出统计报告（按 category/source/language 计数）

### M2 · 风险 Query 生成 agent  → tag: `harm-eval/m2-generator`
1. 接 deepteam attack_simulator 作底层（pip install -e ../AIG-PromptSecurity）
2. 新增 `generators/seed_expander.py`：种子 + (领域, 难度, 语言) → N 条 query
3. 三轴打分器 `generators/scorer.py`：diversity / harmfulness / attackability
4. CLI `aig-eval generate --seed-file X --out Y --n 100`
5. 中文专项 prompt 模板（俚语、谐音、繁简、emoji 混入）
- **验收**：跑 100 条种子 → 输出 500 条扩展 query，三轴分布合理

### M3 · 评分 agent MVP  → tag: `harm-eval/m3-judge`
1. Rubric prompt（中英双版）：label ∈ {safe, soft_refuse, partial_leak, unsafe} + severity 1-5 + dimensions
2. 双 judge ensemble（GPT-4o + Claude-3.5 or Qwen-Max）
3. 不一致 → abstain 队列 → CSV 导出
4. judge 输出 schema v1：`{label, severity, dimensions, evidence, confidence, judge_id}`
5. CLI `aig-eval judge --responses X --out Y`
- **验收**：100 条样本 judge 完成，给出 κ 报告

### M4 · 端到端 pipeline  → tag: `harm-eval/m4-e2e`
1. `pipelines/run_eval.py`：dataset → attack → target → judge → report
2. HTML 报告（按 category × attack_method × severity 矩阵）
3. 失败重试 / 限速 / 断点续跑
4. 一键 demo：`make demo`（10 条种子全流程）
- **验收**：可对任一 OpenAI 兼容 endpoint 一键跑完出报告

### M5 · 校准 + 文档  → tag: `harm-eval/m5-calibration`
1. 300 条人标校准集 spec（不打标，只定流程 + 工具选型）
2. 月度 κ 漂移监控脚本
3. 整套 docs/ 文档
4. PR-ready：可向上游或新 repo 发起

---

## 工程约束

- 不改 upstream 代码，所有新代码在 `aig-harm-eval/`
- Python 3.11+；poetry 或 uv 管依赖
- 每个 milestone 必须：lint + 单测通过 + tag + push
- 大文件 / 数据集走 git-lfs 或外链下载脚本（不入仓库）
- 高敏感数据集（CBRN）不入仓库，只在文档里给下载脚本 + 合规标签

---

## 当前进度

- [x] M0 完成
- [ ] M1 进行中
- [ ] M2
- [ ] M3
- [ ] M4
- [ ] M5
