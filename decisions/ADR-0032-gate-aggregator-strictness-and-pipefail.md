# ADR-0032: gate aggregator 严格化（skipped ≠ success）+ 检测链路 pipefail 修复（P1-3）

- status: accepted（2026-08-20）
- 背景: .github issue #81（自动合并计划）§3.1 工作卡 #84（P1-3）
- 关联: .github/workflows/gate.yml、CI-Workflows/.github/workflows/ci.yml、
  .github/workflows/governance-drift.yml、standards/automation/workflow-path-filtering.md

## 背景

GitHub 官方行为：skipped 的 job 上报状态为 Success，即使是 required check 也不
阻止合并；neutral/skipped 在依赖图中都被当作成功。gate 是组织内唯一 required
check——无人值守下它是唯一合并判据，"绿但没跑"是不可接受的 fail-open 面。

两个 aggregator（.github gate.yml、CI-Workflows ci.yml gate job）此前的断言是
`result != "success" and result != "skipped"` 才算失败——即 **skipped 被当绿**。
路径过滤、`if:` 条件、上游 skip 传导都可能让 gate "绿但没跑"。

**同类活体缺陷（P1-1 T1 期间发现）**：governance-drift.yml 的
`bash governance/drift-check.sh | tee drift-report.txt` 在 Actions 默认 shell
（`bash -e`，无 pipefail）下退出码被 tee 吞掉——drift-check exit 1 时步骤仍
success，"发现漂移则开 issue"（if: failure()）从不触发。实证：run 32331351942
报 4 项漂移但步骤绿、issue 未开。漂移报警机制整体失效。

## 决策

1. 两个 gate aggregator 的断言改为严格相等：`needs` 中任何 job 的
   `result != "success"` 即红（skipped / cancelled / failure / startup_failure
   全部算红）。T3 单元验证：skipped/cancelled/failure/startup_failure → 红，
   success/空 → 绿，全部通过。
2. governance-drift.yml 检测步骤加 `set -o pipefail`——drift-check 的真实退出
   码必须传导到步骤结论，漂移=红=开 issue（GM-1 机制恢复）。
3. 新增 standards/automation/workflow-path-filtering.md：required 链路上的
   workflow 禁用 workflow 级 `paths:`/`paths-ignore:`（check 完全不产生 →
   永久 pending）；job 级过滤必须配 aggregator 显式判定；安全 job 永远不许
   skip。既有例外登记：AI_Web_School contract.yml（非 required 补充检测，
   paths 过滤省额度——不在合并判据链上）。
4. T4 静态扫描（2026-08-20，全组织 11 仓）：除上述登记例外，组织内无
   workflow 级路径过滤。

## 后果

- 上游 job 被 skip 的 PR，gate 变红、不可合并——"绿=真跑过"从此成立。
- hygiene（含 gitleaks/zizmor 安全审计）不存在合法 skip 路径；如未来需要
  条件跳过，必须先修订本 ADR。
- drift 漂移 issue 机制恢复：漂移检出 → run 红 → issue 开；消除 → issue
  自动关闭（该路径一直正常，只是从未被触发过）。