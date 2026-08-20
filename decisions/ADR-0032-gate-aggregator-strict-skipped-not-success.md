# ADR-0032: gate aggregator 严格化——skipped ≠ success + workflow 级路径过滤禁令（P1-3）

- status: accepted（2026-08-20）
- 背景: .github issue #81（自动合并计划）§3.1 工作卡 #84（P1-3）
- 关联: .github 仓 `.github/workflows/gate.yml`、CI-Workflows `ci.yml`、各业务仓 `ci.yml`、
  `standards/automation/required-check-chains.md`、ADR-0029（P1-1）、ADR-0031（P1-2）

## 背景

GitHub 官方行为：skipped 的 job 上报状态为 Success，即使是 required check 也不阻止合并；
neutral/skipped 在依赖图中都被当作成功。合并前全组织的 gate aggregator 断言均为
`result != "success" and result != "skipped"` 才算失败——即 **skipped 被当绿**。任何
路径过滤、`if:` 条件、上游被 skip 的传导，都可能让 gate "绿但没跑"。无人值守下 gate
是唯一合并判据，该 fail-open 面必须焊死（#81 §3.1）。

同时，required check 是字符串精确匹配（`gate`）。workflow 级 `paths:` 过滤会使 check
完全不被产生 → ruleset 静默匹配不到 → "零 required check" → PR 裸奔（#81 §3.2）。

## 决策

1. **严格断言**：全部 aggregator（.github gate.yml、CI-Workflows ci.yml、各业务仓
   ci.yml 的 gate job）改为 `result != "success"` 即红——skipped、cancelled、failure、
   timed_out、startup_failure 一律算红。
2. **结构性预期跳过显式声明**：业务仓存在事件互补设计（`deps` 仅 PR 事件——
   dependency-review API 只支持 PR base↔head 比对；`deps-audit` 仅 push 事件——push 面
   依赖审计）。这些 job 在非自身事件上的 skipped 是结构性的、预期的。aggregator 内以
   `EXPECTED_SKIP[事件]` 白名单显式登记：**未登记的 skipped 一律红**。声明留在
   aggregator 步骤内（与 job 的 `if:` 同文件同评审面），新增事件条件 job 必须同步登记，
   漏登记的结果是 gate 变红（fail-closed 方向）。
3. **安全 job 不许无条件 skip**：事件互补（如 deps/deps-audit）必须保证两个事件面都有
   安全覆盖；纯 `if: false` 式的永久跳过不允许。merge queue（P2-7 #92）接入
   `merge_group` 事件时，须同步扩充对应 EXPECTED_SKIP——本 ADR 预置该义务。
4. **workflow 级 `paths:`/`paths-ignore:` 禁令**：required check 链路上的 workflow 一律
   禁用 workflow 级路径过滤；路径过滤只能用于非 required 的建议性 workflow，并须在
   `standards/automation/required-check-chains.md` 豁免清单登记理由。当前唯一豁免：
   AI_Web_School `contract.yml`（contract-watch，非 required、建议性检测，路径过滤用于
   省 runner）。
5. 规范落盘 `standards/automation/required-check-chains.md` 并入 AGENTS.md 索引
   （P1-2 的 Qodo review 教训：规范不可发现=不生效）。

## 后果

- 上游 job 被 skip 的 PR，gate 变红、无法合并——"绿但没跑"的 fail-open 面关闭。
- 业务仓 aggregator 从 4 行 jq 变为带 EXPECTED_SKIP 声明的显式判定——新增事件条件
  job 的心智负担 +1 行登记，换取漏配置 fail-closed。
- T4 静态扫描基线：全组织 required 链路 workflow 零 workflow 级路径过滤（唯一豁免已
  登记）；后续 drift-check（P1-4 #85 之后续卡）可考虑将此扫描机器化。
