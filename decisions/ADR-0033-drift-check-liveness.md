# ADR-0033: drift-check 活体验证与 PR liveness 侦测（P1-4）

- status: accepted（2026-08-20）
- 背景: .github issue #81（自动合并计划）§3.2/§6 工作卡 #85（P1-4）
- 关联: .github 仓 `governance/drift-check.sh`（§12/§13）、`governance/expected-state.json`
  （liveness 段）、`.github/workflows/governance-drift.yml`、ADR-0029/0031/0032

## 背景

两个无人值守盲区：其一，required check 是字符串精确匹配——ruleset JSON 完全正确
的同时，`gate` job 改名/workflow 重构会让实际匹配为空，变成"零 required check"，
PR 裸奔合并；而 drift-check 此前只对账 ruleset 文本，**文本对账 ≠ 生效验证**。
其二，drift-check 只看治理漂移，不看"流水线卡死"——auto-merge 已开但永不合并、
check 永久 pending、应有而无 check run 的 PR，每周若有几件，人类就还是瓶颈。

## 决策

1. **§12 required check 活体验证**：对每个受管仓拉最近 N 个（默认 20，
   `liveness.required_check_recent_prs`）已合并/打开 PR 的 head sha check runs，
   断言存在名为 `gate` 且 conclusion 非空的 check run；近期无 PR check 活动时
   退化为默认分支 HEAD commit 断言。无任何 check run 的 PR 不作为"gate 缺名"
   证据（归 §13(c) 管）。API 失败一律 fail-closed 报漂移。
2. **§13 PR liveness 侦测**：遍历受管仓 open PR，三类卡死命中即报 DRIFT
   （走既有 auto-drift-report issue 通道，恢复后既有机制自动关闭）：
   (a) auto_merge 已设置但开放时长 > 阈值未合并；
   (b) required check `gate` 处于未完成态超阈值（queued/in_progress 超时）；
   (c) PR HEAD 完全没有 check run（应有而无）。
3. **阈值入期望状态**：`expected-state.json` 新增 `liveness` 段
   （`pr_liveness_hours: 4`、`required_check_recent_prs: 20`）；脚本提供
   `LIVENESS_HOURS_OVERRIDE` env 作测试/排障通道（生效时显式回显，不静默）。
4. **报告通道区分**：governance-drift 工作流按报告内容选 issue 标题——纯
   liveness 告警（`DRIFT PR-liveness` 前缀）用专属标题"流水线卡死/门禁活体
   缺失"，与配置漂移区分处置路径；混合时保持漂移标题。漂移指纹归一化追加
   `开放/已超 NNh → <AGE>h`（卡死 PR 年龄逐小时增长，不归一化则去重失效）。
5. 凭据不扩权：§12/§13 复用 GOVERNANCE_TOKEN（org admin，本就能读各仓
   PR/check runs）；workflow 自身 github.token 仅 issues:write 开报告 issue，
   维持现状。

## 后果

- gate job 改名/workflow 重构导致 required check 落空时，下一次整点 drift-check
  即开 issue 指名（此前完全不可见）；卡死 PR 同理。
- 每 repo 每次检测新增 ≤ 2 + N 次 API 调用（N≤20 PR check runs），小时级频率
  下配额可忽略。
- 误报风险与控制：关闭未合并的 PR 不作为证据；刚创建、check 尚未启动的 PR 由
  阈值（4h）过滤；T3 soak（连续 3 天无假报）作为观察期留在 #85。
