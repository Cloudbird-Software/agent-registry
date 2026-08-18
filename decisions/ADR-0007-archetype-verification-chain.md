# ADR-0007: agent 原型分类（archetype）与三层验证链

- status: accepted
- date: 2026-08-18
- deciders: owner + AI

## 背景

要"可信任的交付"，核心不是不出错，而是**失败可见**。此前 agent 声明缺信任边界维度（谁是生产者、谁是检查者），team 声明缺验证机制，存在自我验收（同义反复）风险。

## 决策

### 1. archetype 七分类（AR-8）

`builder / checker / orchestrator / curator / interface / observer / operator`

- 分类决定：默认权限基线、凭据策略、审计强度（见 agent.schema 描述段）
- 硬约束（validate.py 强制）：checker 必须 private workspace + strict 权限模式；同一声明单 archetype；builder 与 checker 不得同一声明

### 2. 三层验证链（AR-9）

| 层 | 机制 | 声明位置 |
|---|---|---|
| agent 内 | guardrails：output_schema_strict / must_run / forbidden(no-self-test 等) / post_conditions | agent.guardrails |
| team 内 | 独立 checker 验收：不同声明、**不同模型别名**、private workspace；含 builder 的团队强制声明 | team.verification.in_team_check |
| team 外 | persistent 团队周期审计（metrics-anomaly / re-check-sample / retrospective）+ 平台防线（PR gate/ruleset）兜底 | team.verification.external_audit |

- validate.py 强制：含 builder 成员的团队必须有 in_team_check.checkers（原型=checker、非同声明、模型别名不同）；ephemeral 产出型团队必须有 external_audit。
- 审计者自身（governance-core，无 builder）不设内部 checker——由平台防线 + owner 周审兜底（无人可审审计者，防递归）。

### 3. no-self-test 禁则

同一 run 内不得既写实现又写其验收测试；测试来自 checker、既有 golden 或差分（衔接 testing.yaml T-09，防 fake_tests 风险姿态）。

## 后果

- 信任模型一句话：builder 永不自我信任；checker 永不与 builder 合谋；governance-core 永远在外面看着。
- 极端情况（如 checker 全体不可用）人类破玻璃处理，事后回填。
- 未来加 archetype（如 researcher）= C1 变更（改 schema 枚举 + ADR）。
