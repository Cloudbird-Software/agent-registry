# ADR-0004: 团队分 ephemeral/persistent，销毁前强制资产移交（handoff）

- status: accepted
- date: 2026-08-18

## 背景

团队有两类：临时团队（任务制，完成后销毁）和持久团队（持续存在，对仓库与治理组件持续负责）。临时团队销毁时，其工作区、记忆、经验若无移交协议，组织记忆随之中断。

## 决策

1. team 声明必须含 `lifecycle.type`：`ephemeral | persistent`。
2. ephemeral 团组必须声明 `archive_to`（指向 persistent 团队）与 `handoff` 动作清单；`destroy_policy: after-handoff` = 清单全部完成才允许销毁。
3. handoff 动作集：`artifacts-pr`（产出物走 PR 入库）、`memory-distill`（团队记忆提炼）、`skill-extract`（可复用经验固化为 skill）、`adr-write`（关键决策升级 ADR）、`trace-archive`（事件轨迹归档）、`retrospective`（复盘）。
4. 首个持久团队：`team:governance-core`（治理与归档审核）；首个临时团队模板：`team:dev-wave`。

## 后果

- 组织记忆模式：临时团队是工蜂，持久团队是巢穴；资产单向沉淀，可追溯（trace_id/team_id）。
- 临时团队工作区销毁后不可恢复，handoff 完成度由事件流 `run_finished.handoff_done` 审计。
