# ADR-0003: 过程数据三分离——声明与决策进 git，事件进数据库，轨迹进对象存储

- status: accepted
- date: 2026-08-18

## 背景

开发过程会产生大量过程数据（运行事件、对话轨迹、团队记忆、决策理由）。全部进项目仓会导致 clone 臃肿；完全不存则丢失组织记忆。

## 决策

| 类别 | 内容 | 去向 | 生命周期 |
|---|---|---|---|
| 声明与决策 | agent/skill/tool/team 声明、ADR | git（agent-registry） | 永久，PR 评审 |
| 结构化事件 | 五类事件（event.schema） | JSONL append → SQLite/PG（起步 JSONL） | 长期，可聚合 |
| 原始轨迹 | 完整对话、工具入出参全文 | 本地/对象存储，按 trace_id 关联 | 滚动 30 天清理 |

规则：项目仓只放 `AGENTS.md` 索引 + 一行 team 引用；任何项目仓 clone 不携带过程数据。

## 后果

- 审计路径：trace_id → 事件流 → 对象存储取证。
- 周报/统计从事件流聚合，不扫 git。
- ADR 与事件中的 decision_made 对齐：运行中的轻量决策留事件流，影响声明的升级为 ADR（`adr_ref` 回链）。
