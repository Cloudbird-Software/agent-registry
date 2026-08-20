# ADR-0034: required check 活体验证 + PR liveness 侦测（P1-4）

- status: accepted（2026-08-20）
- 背景: .github issue #81（自动合并计划）§3.2/§6 工作卡 #85（P1-4）
- 关联: governance/drift-check.sh（§12/§13 新增）、governance/expected-state.json、
  .github/workflows/governance-drift.yml、ADR-0029（P1-1 对账框架）、ADR-0033（pipefail）

## 背景

两个"文本对账看不见"的盲区：

1. **required check 是字符串精确匹配**。`gate` 是唯一 required check（BP-2），
   job 一旦改名或 workflow 重构，ruleset JSON 完全正确的同时实际匹配为空 →
   "零 required check" → PR 裸奔合并。drift-check §1 只对账 ruleset 文本——
   文本对账 ≠ 生效验证。
2. **流水线卡死不可见**。auto-merge 已开但 >N 小时未合并、check 永久 pending、
   PR head 上应有而无 check run——这些"治理不漂移但流程死了"的形态，此前
   没有任何检测。无人值守下每周卡死五个 PR，人就是瓶颈（#81 §6）。

## 决策

1. **§12 required check 活体存在性**：每个受管仓最近活动的 PR head（无 PR
   活动时退化为默认分支 HEAD）上，必须存在每个 required check 名（从
   rulesets/*.json 的 required_status_checks 派生，单一真源）的 check run 且
   conclusion 非空。缺失即漂移——job 改名/workflow 重构 24h 内检出。
2. **§13 PR liveness 侦测**：遍历受管仓 open PR，三类卡死即漂移（经 GM-1
   既有 issue 通道报告）：
   - `auto_merge` 已设置且 PR updated_at 距今 > 阈值（auto-merge 挂起无进展）；
   - 任一 check run 停留 queued/in_progress 超 > 阈值；
   - PR 创建超阈值且 head 上零 check run（应有而无）。
3. **阈值入期望状态**：`expected-state.json` 增 `pr_liveness_hours: 4`；
   环境变量 `PR_LIVENESS_HOURS` 可覆盖（governance-drift.yml 的
   workflow_dispatch input `liveness_hours` 透传——负向注入测试用，缺省走
   期望状态）。
4. **权限**：检测凭据沿用 GOVERNANCE_TOKEN（org admin，读 check runs / PR
   清单本就需要 org 级读权），workflow job 权限不变（issues:write 开 issue
   已具备）。

## 后果

- gate 假死（改名/重构后 ruleset 匹配为空）最长 1h（小时级 cron）内报漂移。
- 卡死 PR 自动进漂移 issue——"流水线卡死"从被动等人捞变为主动告警。
- 活体验证每仓增加 1-4 次 API 调用（PR 清单 + 至多 3 个 head 的 check runs），
  小时级运行的限流预算内（<5000/h）。
- P1-4 验收测试：T1 改名注入（job gate→gate2 的 PR 自身即注入载体）；
  T2 liveness 注入（dispatch input 调低阈值）；T3 soak 三天观察误报。