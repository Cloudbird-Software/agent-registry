# ADR-0029: 仓库级 auto-merge 纳入期望状态对账（自动合并计划 P1-1）

- status: accepted（2026-08-20）
- 背景: .github issue #81（自动合并计划）工作卡 #82（P1-1）
- 关联: governance/expected-state.json#repo_baseline、governance/drift-check.sh §4、
  governance/apply.sh step5、GOVERNANCE.yaml BP-4、ADR-0017（建仓 bootstrap 遗留）

## 背景

自动合并计划（#81）的第一替换是"人按 merge 按钮 → auto-merge + merge queue"。
`allow_auto_merge` 是仓库级 setting 而非 ruleset 规则——ruleset 管不到这个开关，
它一掉（建仓遗漏、UI 误点、API 变更）auto-merge 全链路就静默死掉。

GOVERNANCE.yaml BP-4 的 intent 已声明"auto-merge 开"，但期望状态
（expected-state.json#repo_baseline）此前只对账 `squash_only / delete_branch_on_merge`，
`allow_auto_merge` 未声明、未对账、未修复——intent 与 enforcement 之间存在盲区。

现状实测（2026-08-20，GraphQL `repository.autoMergeAllowed`）：11 个受管仓中 3 仓
（agent-platform / Shorts_Director / Use-up-Plan）为 false——建仓时序遗漏
（BP-4 apply 覆盖面此前不含该字段，new-repo-init 亦未设置）。

## 决策

1. `expected-state.json` 的 `repo_baseline` 增设 `"allow_auto_merge": true`，
   与 squash_only / delete_branch_on_merge 并列成为全仓基线；豁免继续走既有
   `exclude_repos` 机制（豁免须 ADR 背书，与直推豁免同一纪律）。
2. `drift-check.sh` §4（仓库基线对账）增断言：REST 字段 `allow_auto_merge`
   必须等于期望值；字段读不到（null，如凭据缺 administration 读权限的
   fine-grained PAT）按漂移报告——fail-closed：检测器失明不得伪装成无漂移
   （与 §4 仓库清单 fail-closed、§8 关联 PR 查询 fail-closed 同一纪律）。
3. `apply.sh` step5（仓库基线幂等修复）的 PATCH 体增 `allow_auto_merge`
   （值自 expected-state.json 派生，保持期望状态单一真源）。
4. GOVERNANCE.yaml BP-4 的 verify 声明同步：drift-check §4 显式覆盖 repo settings
   （含 allow_auto_merge），频率 hourly（对齐 GM-1 小时级检测的现实）。
5. 本 ADR 作为 .github 仓 P1-1 变更 PR 的 adr-required 引用背书（C1）。

## 后果

- 3 个现存 auto-merge-off 仓在下一次小时级 drift-check 即报漂移并开 issue；
  修复路径 = `GH_TOKEN=<org admin> bash governance/apply.sh`（幂等）。
- 本地预检语义变化：缺 administration 读权限的凭据跑 drift-check §4 必报
  auto-merge 漂移（字段 null）——这是 fail-closed 的预期行为，不是误报；
  CI 的 GOVERNANCE_TOKEN 已实测可读该字段（2026-08-20 run 32323856756 §4 全绿）。
- P1-2（#83）的"App 实测 enable auto-merge"依赖本卡把开关补齐为 true；
  P1-4（#85）的 PR liveness 侦测（auto-merge 已开但 >N 小时未合并）以本对账为基础。
- 不改变 ruleset 面：main-protection 的 required check / merge method 约束不动
  （gate 仍为唯一 required check；squash-only 不变）。
