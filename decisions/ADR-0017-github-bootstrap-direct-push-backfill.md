# ADR-0017: .github 破玻璃直推回填——Trae 工具产物与误入 gitlink

- status: accepted
- date: 2026-08-19
- deciders: owner + AI
- resolves: drift-check §8 报警的两个非 PR commit（9b056b3a / 416f5f5）按 ADR-0006 完成 24h 内回填（PR + ADR）

## 背景

.github 在治理已生效（policy_effective 2026-08-19T00:00Z；PR 流程自 08-18 即运转，见 PR #19）期间出现两次连续 admin 直推（9b056b3a 01:44、416f5f5 02:03，同题"feat: GitHub 企业级安全与质量体系搭建"，父提交 f3974a6 = PR #19 合并提交）。与 f3974a6 对比，两次直推的净变更为两项：

1. 新增 `.trae-html-share-packages/scripts/create-cloudbird-agent-app.html.zip`（Trae IDE 分享机制产出的工具页面打包）；
2. 新增 `agent-registry` gitlink（mode 160000、无 .gitmodules）——工作区误 `git add` 的产物。

后果：gitlink 使 actions/checkout 在 main 与全部 PR 上一律失败（gate/scorecard 双红、5 个 open PR 被阻塞），后由 PR #52 移除修复；drift-check §8 将持续报警至两个 commit 滑出 7 天检测窗口（2026-08-26）。

## 决策

1. 追认该两次直推为破玻璃事件，本 ADR 即其回填记录（ADR-0006 三件套：本 ADR + 本 PR；无在案漂移 issue——事发当日 03:00 的 drift 工作流因 gitlink 无法 checkout 未出报告，事故与修复见 PR #52）。
2. 净变更定性：zip 为 Trae 工具分享产物（保留在库）；gitlink 为误提交（已由 PR #52 删除——REPOS.yaml 头部明确本组织"替代 submodule 方案"）。两次直推不涉及任何治理实质内容变更。
3. 教训登记：IDE 会话产物目录（.trae-html-share-packages/）与本地兄弟仓克隆（agent-registry 等）不得随治理变更一起提交；后续考虑将该目录加入 .gitignore（另行 PR，不在本 ADR 范围）。

## 后果

- 破玻璃留痕闭环：初始引导之外的直推无先例可援引，此后 §8 报警一律按未回填破玻璃处置。
- §8 对这两个 commit 的后续每日报警（至 08-26）视为已回填已知项，不触发新的处置动作。
