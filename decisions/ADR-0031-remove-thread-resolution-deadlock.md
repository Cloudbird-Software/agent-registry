# ADR-0031: 拆除 required_review_thread_resolution 死锁 + 机器反馈通道规范（P1-2）

- status: accepted（2026-08-20）
- 背景: .github issue #81（自动合并计划）§2.2 工作卡 #83（P1-2）
- 关联: governance/rulesets/main-protection.json、standards/automation/bot-channels.md、
  ADR-0029（P1-1 allow_auto_merge 对账）、agent-registry PR #45（App auto-merge 实测）

## 背景

main-protection ruleset 的 `required_review_thread_resolution: true` 在有人的团队
是好规则，在无人值守下是永久 pending 的定时炸弹：CodeQL、任何 review bot、
随手一条 comment，只要 unresolved，auto-merge 永远不触发，而没有人去点 resolve。
组织没有第二个 reviewer，该条件只剩死锁语义。

实测补充（2026-08-20，agent-registry PR #45）：AG-1 App（cloudbrid-agent）token
`gh pr merge --auto --squash` enable auto-merge 成功（contents+PRs:write 足够，
`auto_merge.enabled_by = cloudbrid-agent[bot]`），gate 绿后 PR 无人触碰自动合并
——组织首个全自动合并闭环。#81 §2.1 要求的"实测而非假设"已满足。

## 决策

1. `main-protection.json` 的 `required_review_thread_resolution` 改为 `false`
   （#81 §2.2 三选一之推荐项：直接从 required 条件移除；不采用 GraphQL
   resolveReviewThread 自动清理——被审者关闭审计意见语义不可接受）。
2. 新增 `standards/automation/bot-channels.md`：机器意见只走 check run
   annotation / 普通 PR comment，禁止机器创建 review comment/review thread；
   禁止机器 resolve 人类 thread；机器不得自我授权（approve/洗红灯/替代确定性
   检查）。为未来重启 thread 门或引入 reviewer agent（#97 veto-only）预置约束。
3. ruleset 变更经 .github PR 合并后由 apply.sh §1 应用；drift-check §1 文本
   对账自动跟随。

## 后果

- 存在 unresolved review thread 的 PR 不再阻塞合并（合并判据收敛为：gate
  required check 绿 + squash-only + 线性历史）。人类 review 意见的处置责任
  移交给：CODEOWNERS owner-only review（C1 路径）+ P3-3 veto-only reviewer
  agent（#97）+ P3-4 每周抽样审计（#98）。
- bot 若未来产生 review thread（违反规范 1），不再卡死合并，但违反行为由
  抽样审计（#98）追责；thread 门重启须新 ADR。
