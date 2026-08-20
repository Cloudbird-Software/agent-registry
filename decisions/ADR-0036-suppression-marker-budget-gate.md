# ADR-0036: 抑制标记预算门——豁免配额化与总量棘轮（P2-2）

- status: accepted（2026-08-20）
- 背景: .github issue #87（自动合并计划 P2-2，父计划 #81 §4.1「测试篡改与抑制配额」）
- 关联: CI-Workflows `scripts/suppression-budget.sh`、`policy/suppressions.yaml`、
  `.github/workflows/check.yml`（接入）与 `.github/workflows/ci.yml`（自测）；
  .github `governance/policy/testing.yaml`（fake_tests 风险敞口）；ADR-0032（aggregator
  严格断言——本门的接入范式）；ADR-0029（auto-merge 前提——本门是"开了不炸"侧）
- scope: suppression-budget（逃生门 scope 标记：PR 引用本 ADR 时，
  CI-Workflows `policy/suppressions.yaml#escape_hatch.scope_marker` 以本行字样匹配判定 scope 覆盖）

## 背景

抑制标记是 agent 让门禁变红的第二条捷径：lint 红就加 noqa，类型错就加
`type: ignore`，泄密扫描红就加 gitleaks 豁免。无人值守（auto-merge）下，
每个抑制标记都是一次未被审判的门禁豁免——测试篡改检测门（P2-1 #86）堵的是
"改判据"，本门堵的是"就地消音"。逐条人审不可扩展，替换物是**配额制**：
零星合理豁免（≤3/PR 且总量不升）自动通过，批量规避被硬拦，越界者走
ADR 逃生门入账。

## 决策

1. **标记全集落盘 policy（机器可解析）**：`CI-Workflows/policy/suppressions.yaml`
   声明抑制标记全集——正则类（POSIX ERE，`grep -E` 同引擎）：noqa、eslint-disable、
   `type: ignore`、`pyright: ignore`、nosec、`pragma: no cover`、`coverage: ignore`、
   istanbul ignore、`gitleaks:allow`、`depcruise:ignore`（arch-lint 行内豁免）；文件类：
   `.gitleaksignore` 非空非注释行每行计 1。新增标记类型只改 policy（C1 路径，
   ADR + owner review），不改脚本。
2. **单 PR 净增阈值**：diff 中抑制标记净增量（新增 − 删除）>
   `per_pr_max_net_add`（初始 3）→ 红。阈值为 policy 参数而非脚本常量——
   后续 `governance/expected-state.json` 可直接对账声明（本卡不动 expected-state，
   主 agent 集成）。
3. **总量棘轮**：以 2026-08-20 全 11 仓基线盘点落盘各仓标记总量为初始基线；
   PR 合入树总量 > 基线 → 红（持平/下降绿）。基线只许经 policy 修订下调或
   逃生门豁免后上调——"累计总量不得上升"是硬不变式。盘点结果全 11 仓总量
   为 0：零起点下总量维度先于单 PR 配额生效（任何净增即红，须经逃生门入账
   并上调基线；此后 ≤3 配额在新基线内正常运转）——这是"累计不升"验收
   标准的直接后果，不是缺陷。
4. **逃生门（与 P2-1 同款机制）**：PR title/body 引用 ADR-NNNN，且该 ADR
   文件（agent-registry/decisions/）内容含 `escape_hatch.scope_marker` 字样
   （scope 覆盖本门）→ 豁免转绿。入账 = 判定输出显式记录豁免 ADR 编号、
   净增量、合入总量 vs 基线，并声明棘轮同步义务（豁免方须在后续 PR 将基线
   上调至新总量，否则下一个 PR 即红——豁免不等于棘轮失效）。幽灵 ADR
   （引用不存在）不豁免。
5. **fail-closed**：diff/树/policy 任一获取或解析失败、仓库无基线声明、
   policy schema 违规、PyYAML 不可用——一律红，检测器失明不得伪装通过。
6. **接入与生效面**：实现为 `check.yml` 内部 job `suppression-budget`
   （PR 事件限定；push 面无 diff 语义，结构性跳过——caller 侧 `uses:` job
   聚合结果不受内部 skip 影响，符合 ADR-0032 严格断言语义）。业务仓零
   caller 改动：`@v1` 指针移动后全量生效（移动前须在一个业务仓实测
   `GITHUB_WORKFLOW_REF` 解析出 CI-Workflows 自身 ref——发布清单项）。
   脚本/策略钉在被调 workflow 同 ref（PR 改不到审判自己的逻辑，#81 §3.3
   同源防线）。CI-Workflows 自身以 `ci.yml` 自测 job（T1–T5 场景干跑）
   纳入 gate needs 链。
7. **计数排除面收敛**：仅 CI-Workflows 自身可声明排除路径
   （`policy/suppressions.yaml`、自测脚本——模式声明与 fixture 是数据不是抑制）；
   业务仓零排除项，"挪目录洗标记"无通道。

## 后果

- 净增 ≤3 且总量不升的 PR 绿（含净减）；净增 >3 或总量上升 → 红，
  两种红因错误信息显式区分。
- 大规模豁免（重构批量加 noqa 等）必须走 ADR——把"逐条人审"替换为
  "配额 + 越界才叫人"，人审频次从每豁免一次降为每 ADR 一次。
- 已知保守性：散文/文档中按标记语法书写的示例字样会被计入（如文档里
  写 `# noqa` 示例）。方向为 fail-closed（多计不少计），由预算与逃生门吸收。
- 基线棘轮生效后，任何使总量上升的合入（含文档示例）都需 policy 同步
  或 ADR 豁免；#98（P3-4）的熵增指标可消费本门数据产出。
- 待办移交：expected-state 声明阈值对账（主 agent 集成）；P2-1 落地时
  复用同一逃生门与入账格式，减少各仓 caller 改动。
