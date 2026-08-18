# ADR-0012: team.schema v2 对齐实例语义 + check:* 防线注册表

- status: proposed
- date: 2026-08-18
- deciders: owner + AI
- resolves: ADR-0011(team-collaboration) 遗留项两项
- cross-repo: Cloudbird-Software/.github#16（L0 team.schema v2）

## 背景

ADR-0011（团队协作标准 v1.0，本仓 PR#7）定稿时留两项遗留：其一，L0 team.schema 需增
`destroy_condition` 字段与 `re-check-sample` 枚举值——实例侧（registry/teams/ 三团队）已按
v1.0 语义对齐，schema 落后；其二，声明中散落的 `check:*` CI 防线名无注册表——引用不存在的
check = 声明了不存在的防线。

对第二项做摸底时证实了悬空风险是真实的：`adr-required` 被 profiles enforced_by、
curator post_conditions、CT-CUR-003 expected 三处引用，但**无任何 CI job 实装**
（各仓 CI 仅 gate 聚合 job）——控制测试声称的防线行为当前不可执行。

## 决策

1. **team.schema v2（跨仓 .github#16）**：
   - `lifecycle.destroy_condition`（遗留项）：销毁**语义**条件，与 `destroy_policy:
     after-handoff` 是 AND 关系——移交完成只表达"资产安全"，不表达"任务语义上该结束"
     （dev-wave: released_behind_flag OR reverted；incident-cell: exit_criteria 满足）。
     destroy_scope（agent 实例与临时 workspace；数据层制品不随队销毁）入 description。
   - `coverage` 枚举增 `re-check-sample`（遗留项）：前道全审+后道抽检复核的双层验证
     （attention-ledger.sampled 语义——curator 全审在前、owner 抽检 10% 复核）。
     external_audit.method 的 re-check-sample（审计方法）v1 已有；本变更使 coverage
     （验收覆盖）同可表达。
   - 同类滞后一并清理（不留新遗留）：topology +single-seat、frequency +per-incident、
     handoff +incident_report/retro_24h/followup_backlog_merge/retro_debt_tracking、
     lifecycle +trigger/ttl/on_ttl_expiry、顶层 +archetype/scope/budget/backlog_role、
     members +seat、orchestration +phases_ref/release/authorization_ref、assign/merge
     三选一枚举废弃为机制描述 string、layout +contracts/findings/backlog、
     governance-core 引用更正为 stewardship（v1.0 拆分）。
   - 验证方法（可复跑）：jsonschema Draft202012 对三实例校验——v1 下 13 处不符
     （dev-wave 3 / incident-cell 7 / stewardship 3），v2 全 PASS。

2. **standards/checks.yaml 注册表 + validate fail-closed 校验**（本仓）：
   - 登记 9 项 check（gate/intent-ratified/test-tree-freeze/pr-identity-path-matrix/
     adr-required/rollback-plan-required/flag-enable-owner-only/retro-debt-aging/
     precedent-non-normative），每项 status（active|planned）+ where（实现/计划位置）。
   - validate.py 两向校验（与 side-effects 词表、ct-coverage 同模式）：
     正向——standards/ 与 registry/ 一切 `check:<id>` 引用必须 ∈ 注册表（未登记=悬空
     防线=CI 拒绝；文本级扫描，因引用嵌在 description/enforced_by/post_conditions 自由文本）；
     反向——登记但无消费方 = 注册表漂移（consumed_externally 标记平台仓消费的条目，如 gate）。
   - 负向测试已验证：注入 `check:nonexistent-guard` → validate FAIL exit=1，报悬空防线。
   - planned 语义：引用合法但显式声明未实装（pr-identity-path-matrix 随 ADR-0010 二期；
     precedent-non-normative 随 case_law on_trigger；adr-required 见决策 3）。

3. **发现与待办（显性化而非掩盖）**：
   - `adr-required` 无 CI 实装：登记 planned，CT-CUR-003 的 expected 在实装前不可执行
     （现行防线=CODEOWNERS owner-only review CT-CUR-002 + main-protection ruleset）。
     实装待办：validate.yml 增 job——PR 触及 C1 路径（standards/、decisions/、scripts/、
     .github/、CODEOWNERS）且 body/diff 无 `ADR-\d{4}` 引用则 fail（C1 流程机器化）。
   - ADR 编号冲突：main 现存两个 ADR-0011（runtime-egress：供应链线，PR#6；
     team-collaboration：团队协作线，PR#7）。两 PR 均已合并、授权凭证完整，不重编号
     （引用面不对称：本仓 30+ 处 vs 0 处）。**消歧约定：引用 ADR-0011 必须带主题限定**
     （ADR-0011-team-collaboration / ADR-0011-runtime-egress）；新 ADR 自 0012 顺延。

## 后果

- L0 schema 与实例的同步演进有了可复跑的验证基线（jsonschema 校验可入 CI——二期可考虑
  submodule 拉取 L0 schema 自动校验，本 PR 以注册表+人工对齐起步）。
- 声明中的防线引用 fail-closed：新增 check:* 引用必须先登记，"假防线"从无法发现变为
  CI 拒绝。
- 注册表自身有反向漂移检测（登记项须有消费方），与 ct-coverage 一一对应原则对齐。
- 代价：引入新 check 的变更多一步登记（standards/checks.yaml 走 C1 流程）——与
  "流程声明的变更成本应与其影响半径成正比"一致。
