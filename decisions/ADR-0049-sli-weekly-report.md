# ADR-0049: 自动合并 SLI 周报与每周抽样审计

日期：2026-08-21 ｜ 状态：已接受 ｜ 关联：.github #98、#81 §8、ADR-0032/0036/0039/0041/0043

## 背景

自动化程度不能凭感觉（#81 §8）。无人值守后需要数据回答"是否成功"：自动合并率、
人类触碰数/merged PR（目标→0）、门禁逃逸率（被 revert+事后发现/周——须有分母）、
卡死 PR、PR 停留 P95、假红率、熵增指标。同时把 review 从 100% 覆盖降为统计抽样
（每周 3 个随机已自动合并 PR 审计），使人类判断成本与 PR 数量脱钩。

## 决策

1. **SLI 采集**（scripts/sli-report.sh + sli-weekly.yml，.github 仓）：
   auto_merge_rate（agent 身份合并/全部合并，分母=窗口内合并 PR）、
   escape_rate（合入 [auto-revert]+post-merge P0 issue / 合并 PR——有分母）、
   stuck_prs（open>48h）、pr_duration_p95、flaky_rate 与 entropy 先标 pending
   （数据源 ADR-0043/0036/0039 滚动接入，不阻塞上线）。
2. **周期**：每周一 01:30 UTC 自动跑 + workflow_dispatch 注入（窗口/抽样数可覆盖）。
   产出 sli-report 标签 issue（周环比 + 指标口径注明分母）。
3. **抽样审计**：从窗口内 agent 合并 PR 随机抽 3 个开审计 issue；seed=ISO 周
   （可复现、防"挑软的抽"）；checklist：改动与宣称相符/门禁判定正确/事后问题回流。
4. **阈值升级**：escape_rate>0 连续两周 → 自动开 P1 issue（归因义务）。
5. **fail-closed 与自测**：API 拉取失败 exit 2；执法前跑离线自测 7 断言
   （T2 分母陷阱 N/A、T3 抽样复现/无偏卡方粗检、T5 阈值判定）。

## 后果

- 零合并周输出 N/A 而非除零或 100%（T2 语义固化）。
- 抽样可复现性使"挑软样本"质疑可被证伪。
- escape_rate 是唯一的风险指标：分母=合并 PR 数，分子含演练数据时须人工归因剔除
  （演练 PR 标题含 test: 前缀可过滤——首版未自动过滤，记为已知噪音源）。
