# AIG Harm-Eval

> 在 [AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard) 之上构建的"大模型攻击 + 回复安全评测"扩展子项目。
> 三大子系统：**数据集收集** · **风险 Query 生成 Agent** · **评分 Agent**。

## 目录

- `docs/RESEARCH.md` — 上游能力盘点 + 缺口分析
- `schema/` — 统一数据 schema v1（含 JSON Schema + 说明）
- `adapters/` — 外部数据集 → schema v1 转换器
- `generators/` — 风险 query 生成与三轴打分
- `judges/` — 评分 agent（rubric + ensemble）
- `pipelines/` — 端到端评测流水线
- `PLAN.md` — 里程碑路线图

## 设计原则

1. 不改上游代码，所有改动隔离在本目录
2. 数据 / 攻击 / 评分三层解耦，可独立替换
3. 评分以"多维 rubric + ensemble + 校准"为主，不追求单 judge 二元判定
4. 高敏感数据集（CBRN/未成年人）默认不入仓库，仅留下载脚本 + 合规审查痕迹

## 状态

WIP — M0 完成（仓库初始化 + 调研 + schema v1）。详见 PLAN.md。
