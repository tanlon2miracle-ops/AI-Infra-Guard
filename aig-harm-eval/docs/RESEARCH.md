# AI-Infra-Guard / AIG-PromptSecurity 调研报告

> 目标：评估在该框架上自建"大模型攻击 + 回复安全评测"三大子系统（数据集 / 风险 query 生成 agent / 评分 agent）的可行性与缺口。
> 时间：2026-05-21
> 上游：https://github.com/Tencent/AI-Infra-Guard  (fork: tanlon2miracle-ops/AI-Infra-Guard)

---

## 1. 框架定位

A.I.G 是腾讯朱雀实验室的一站式 AI 红队平台，主要模块：
- ClawScan（OpenClaw 安全体检）
- Agent Scan（Dify/Coze 等 Agent 工作流）
- MCP Server & Agent Skills Scan
- AI Infra 漏洞扫描（64 种组件 / 1300+ CVE）
- **Jailbreak Evaluation = AIG-PromptSecurity 子模块**（我们关心的部分）

AIG-PromptSecurity 基于 deepteam 派生，主入口 `cli_run.py`，核心流程：
`数据集 → attack_simulator → target_model 调用 → metrics judge → 报告`。

---

## 2. 现有资产盘点

### 2.1 数据集（`data/eval/` + deepteam 生成器）

静态 JSON 13 个：
- CBRN-weapon / cyberattack / violent / privacy-leakage / misinformation / unethical-behavior / copyright-violation / non-violent-illegal-activity
- ChatGPT-Jailbreak-Prompts / JailbreakPrompts-Tiny / JailBench-Tiny
- JADE-db-v3.0（清华 JADE）
- HarmfulEvalBenchmark

deepteam `vulnerabilities/` 14 类（自动生成 baseline query）：
bias / competition / excessive_agency / graphic_content / illegal_activity / intellectual_property / misinformation / personal_safety / pii_leakage / prompt_leakage / robustness / toxicity / unauthorized_access / custom(+custom_prompt) / multi_dataset

### 2.2 攻击 / 风险 query 生成（`deepteam/attacks/`）

single_turn (18)：
- encoding / stego / multilingual（变形）
- roleplay / prompt_injection / system_override / super_user / permission_escalation / goal_redirection / input_bypass / context_poisoning / semantic_manipulation / promisqroute / stratasword / gray_box / icrt_jailbreak / math_problem / equa_code / raw

multi_turn (6)：
- crescendo_jailbreaking（渐进升级）
- tree_jailbreaking（搜索式）
- linear_jailbreaking
- bad_likert_judge
- best_of_n
- sequential_break

调度核心：`attack_simulator/attack_simulator.py` (719 行)。

### 2.3 评分（`deepteam/metrics/`）

- 总体 jailbreak 判定：`metrics/is_jailbreak/is_jailbreak.py`（170 行，单 LLM judge）
- 分类 metric（每类一个）：bias / toxicity / pii / hijacking / hallucination / harm / illegal_activity / personal_safety / misinformation / intellectual_property / overreliance / imitation / competitors / contracts / excessive_agency / graphic_content / prompt_extraction / debug_access / shell_injection / sql_injection / ssrf / rbac / bola / bfla / random_metric

---

## 3. 三大子系统：现状 vs 缺口

### 3.1 数据集收集

| 维度 | 现状 | 缺口 |
|---|---|---|
| 覆盖类目 | 13 个 JSON + 14 类生成器 | 缺主流开源集：HarmBench / AdvBench / StrongREJECT / SimpleSafetyTests / SALAD-Bench / BeaverTails / Do-Anything-Now / TruthfulQA-Adv |
| Schema | 各 JSON 字段不统一 | 无统一 schema（id / prompt / category / sub_category / source / language / difficulty / severity / hash / license） |
| 元数据 | 缺 | 无来源溯源、无版本号、无中英分布统计、无难度/危害度标签 |
| 质量控制 | 缺 | 无去重（精确 + 近似）、无训练污染检测（vs 主流 SFT/RLHF 数据） |
| 更新机制 | 静态 | 无在线拉取/版本订阅/diff 流水线 |
| 领域细分 | 弱 | 缺金融、医疗、政务、未成年人、版权、广告合规等垂类专项 |

### 3.2 风险 Query 生成 Agent

| 维度 | 现状 | 缺口 |
|---|---|---|
| 攻击手法 | 24 种（变形包装为主） | 已较全 |
| 种子扩展 | 弱：以"变形已有 prompt"为主 | 缺"风险点 → 多样化新 query"语义扩展（同义改写、场景迁移、角色注入、多轮拼接） |
| 质量打分 | 缺 | 生成的 query 无多样性/危害性/可攻击性三轴打分 |
| 难度分级 | 缺 | 无 easy/medium/hard 自动分层、无 curriculum |
| 领域定制 | 缺 | 无"输入领域 + 法规条款 → query"的领域 agent |
| 中文优化 | 一般 | 多语攻击有，但中文母语化（俚语、方言、谐音、繁体、火星文）覆盖弱 |
| 反馈闭环 | 缺 | judge 结果不回流，无"哪类种子最容易破防"的反馈强化 |

### 3.3 评分 Agent

| 维度 | 现状 | 缺口 |
|---|---|---|
| 总判定 | 单 LLM judge（is_jailbreak） | 无 ensemble / 无置信度 / 无 abstain |
| 分级 | 二元（pass/fail） | 缺多级 rubric：safe / soft-refuse / partial-leak / unsafe + severity 1-5 |
| 维度 | 单一"是否越狱" | 缺多维度：危害度 / 合规 / 真实性 / 偏见 / 隐私 / 拒答质量 |
| 一致性 | 缺 | 无 self-consistency、无 swap test、无 judge 间 Cohen's κ |
| 中文 judge | 缺专项 | 现 judge 偏英文 prompt 设计 |
| 校准 | 缺 | 无 human-label 集合校准、无误判审计 |
| 可解释 | 缺 | 仅给标签，无 evidence span / rule trigger |
| 拒答质量 | 缺 | 过度拒答（over-refusal）不计入，模型容易拿"全拒"刷分 |

---

## 4. 设计建议（MVP 三步走）

### Step 1 — 数据集层（最小闭环）
1. 定义统一 schema（含 source / license / language / category / severity / difficulty / hash）
2. 拉 3 个外部集：HarmBench、StrongREJECT、SALAD-Bench → 转 schema
3. 与现有 13 JSON 合并 → 去重 → 出 `dataset_index.json` + 统计报告

### Step 2 — Query 生成 agent（增量补缺）
1. 接 deepteam `attack_simulator` 作为底层（不重写）
2. 新增 `seed_expander_agent`：种子 + 领域 + 难度 → N 个多样化 query（带三轴打分）
3. 接 over-refusal 反例集（避免 judge 偏移）

### Step 3 — 评分 agent（重点投入）
1. Rubric 多级评分（safe / partial / unsafe + severity 1-5 + dimension 标签）
2. 双 judge ensemble（中英 prompt 各一）+ 不一致触发 abstain → 进人工队列
3. 校准集（300-500 条人标）+ 月度 κ 报告
4. 输出 evidence span / 触发规则 / 置信度

---

## 5. 接入策略

- 不分叉 deepteam，作为 git submodule / pip 依赖
- 新代码放 `aig-ext/`：`datasets/` `generators/` `judges/` `pipelines/`
- 复用 A.I.G 的 cli_run 入口，新增 `--profile harm-eval-v1`
- 评测产物统一格式：`{prompt, attack_method, response, judge: {label, severity, dimensions, evidence, confidence}}`

---

## 6. 风险 / 注意

- 部分数据集（CBRN、爆炸物制造）**许可证敏感**，落盘前需过法务/合规
- judge 模型选择影响极大；建议至少跑过 GPT-4o + Claude + 国产强模型三家做交叉
- 中文领域 judge 训练样本不足，初期靠"强 LLM + rubric prompt"，后续再蒸馏
- A.I.G 上游迭代快（每月 release），fork 要定期 rebase

---

## 7. 下一步动作

1. [ ] 确认要纳入的外部数据集白名单（含合规审查）
2. [ ] 落统一 schema v1 + 写转换脚本
3. [ ] 选 judge 模型组合（建议：GPT-4o + Claude 3.5 + Qwen-Max）
4. [ ] 出 MVP 评测 pipeline（10 个种子 × 3 攻击 × 双 judge）跑通端到端
5. [ ] 校准集人工标注规范 + 标注工具选型
