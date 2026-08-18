# ADR-0006: 治理仓变更分级流程与破玻璃回填制

- status: accepted
- date: 2026-08-18
- deciders: owner + AI

## 背景

治理仓（.github 的 governance/standards、agent-registry、CI-Workflows workflows/）是全组织强制的唯一真源，但此前变更约束是 advisory（GM-2"禁止网页手改"仅靠自觉），且 .github 仓自身被排除在 main-protection 之外；AI 与 owner 均发生过直推（bypass）。需要"人机同受约束"的流程，且破玻璃必须留痕。

## 决策

1. 变更分三级（GOVERNANCE flows.governance_change）：
   - C1 治理意图（GOVERNANCE/rulesets/expected-state/standards/models.yaml/decisions）：PR + **ADR（无 ADR 不合并）** + drift-check 本地预检
   - C2 注册条目（agent-registry/registry/、业务仓 AGENTS.md/CODEOWNERS）：PR + validate.py
   - C3 文档注释：PR
2. 授权凭证 = ADR + PR 记录（单人公司自批无意义，凭证是"决策可追溯 + 变更不可绕过"）。
3. 破玻璃：admin 直推（ruleset bypass）允许用于紧急回滚，24h 内必须回填 PR + ADR + 漂移 issue 说明。
4. 监控：drift-check 新增 §8——policy_effective(2026-08-19) 之后受治仓默认分支的非 PR commit（消息无 (#N) 后缀）= 漂移，每周检出即开 issue。
5. main-protection 解除 .github 豁免，治理仓与业务仓同受 PR+gate+线性历史约束；.github 增设自有 gate 工作流（YAML/JSON 解析 + 脚本语法）。
6. 两治理仓增设 CODEOWNERS 声明归属（owner）。

## 后果

- owner 与 AI 的每一次治理变更都有 PR+ADR 双记录；直推自动暴露。
- 历史直推（含 2026-08-18 agent-registry 的两次）因 policy_effective 在其后而豁免，属流程建立前存量。
- 紧急情况不堵路：bypass 保留，代价是 24h 回填义务 + 自动曝光。
