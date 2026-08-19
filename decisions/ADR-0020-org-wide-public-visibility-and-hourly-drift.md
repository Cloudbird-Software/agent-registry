# ADR-0020: 组织全仓公开政策与可见性小时级漂移检测

- status: accepted
- date: 2026-08-19

## 背景

ADR-0019 修正了 agent-registry 的可见性申报（private→public），但暴露两个结构性缺口：

1. **政策未明示**：REPOS.yaml 允许逐仓声明 visibility，申报值本身可以是 private——"组织全公开"只存在于惯例（flows.new_repo `--public` 建仓），从未成文。错误申报正是 ADR-0019 的根因；地图里 agent-tools（planned）同样声明着 private。
2. **检测盲区 24h**：governance-drift 每日 03:00 UTC 运行一次，可见性被改回 private 最长一天无人知晓。

## 决策

1. **全仓公开（all-public）政策**：组织下一切仓库必须 public。无豁免路径——REPOS.yaml 的 `exempt` 状态只豁免治理基线（repo_baseline），不豁免可见性。未来确需私有仓，须新 ADR 推翻本决策。
2. **检测强化**（drift-check.sh §7）：
   - §7a 增强：申报 `visibility ≠ public` = drift（申报侧政策校验——堵 ADR-0019 式错误申报）；
   - §7b/c 合并遍历：线上全量仓逐一查 `private` 即 drift——**不依赖申报完整性**（未申报仓的可见性同样受检），新建私有仓一小时内必被检出。
3. **频率**：governance-drift 由每日改每小时（`0 * * * *`）。公开仓 Actions 免费；检测为轻量只读 API 调用，org 当前仓量级下配额可忽略。
4. **落地**：REPOS.yaml 全部 `visibility: public`（agent-registry 修正 + agent-tools 计划仓政策先行声明——建仓时必须 `--public`，否则首检即 drift）。GM-4 intent 收录政策，verify frequency 升为 hourly。

## 后果

- 可见性漂移盲区 24h → 1h；"改回私有"类操作（无论何种来源）一小时内进 drift 报告。
- 检测与申报解耦：即使地图漏报，可见性仍受检（§7b 照旧报未申报——两条防线独立）。
- .github PR #62（agent-registry 单点申报修正）被本决策落地 PR 取代（superseded）。
- 成本：每小时一次 workflow 运行（~1min，公开仓免费额度）。
