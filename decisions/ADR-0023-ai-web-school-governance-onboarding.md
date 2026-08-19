# ADR-0023: AI_Web_School 纳入组织治理基线

- status: accepted（2026-08-19）
- 背景仓库: .github / AI_Web_School / agent-registry
- 关联: GOVERNANCE.yaml BP-1/CI-1/SC-1/SC-3/AG-4/RL-1/GM-4、REPOS.yaml、governance/expected-state.json

## 背景

AI_Web_School 是本组织唯一的历史产品仓（小学语数英个性化练习平台，Python 3.12 +
FastAPI + PostgreSQL 16，2026-07 建仓，先于组织治理基线成形）。因此在治理版图中
被登记为 `status: exempt`，并在三处被显式排除：

1. `governance/expected-state.json` repo_baseline.exclude_repos（BP-4 仓库基线不适用）
2. `governance/rulesets/main-protection.json` repository_name.exclude（BP-1/BP-2 不适用）
3. `governance/rulesets/codeql-gate.json` repository_name.exclude（SC-1 不适用）
4. `governance/rulesets/release-tags.json` repository_name.exclude（BP-3 不适用）
   （勘误 2026-08-19：初版漏列本条，经 .github PR #76 机器人评审发现后补入）

豁免的直接代价已经发生：2026-08-19 PR #31 在 pr-check **未通过**（7 个单测失败：
response_event 按月分区 vs 测试硬编码历史日期的跨月时间炸弹）的状态下被合入 main
——无 required check 即无合并防线，仓库红灯两日无人拦截。这与组织"gate=唯一合并
前置"的治理意图直接冲突，历史豁免不再有存在理由。

仓库线上设置经核验已符合基线（squash-only / 合并删分支 / auto-merge 开 / wiki 与
projects 关 / public），CodeQL default setup 已于 2026-08-18 启用，admin 唯一
（randypanding），具备直接纳管条件。

## 决策

1. **解除全部豁免，转入 active**：
   - expected-state.json repo_baseline.exclude_repos 置空；
   - main-protection.json / codeql-gate.json / release-tags.json 的
     repository_name.exclude 移除 AI_Web_School（codeql-gate 保留 .github 自身豁免不变）；
   - GOVERNANCE.yaml BP-1 的 exception 字段移除；
   - REPOS.yaml 中 AI_Web_School `status: exempt → active`，角色描述更新为
     已接入治理面的产品仓。合并后按 GM-2 流程跑 apply.sh 落地 ruleset 变更。
2. **仓库侧治理面落地（AI_Web_School PR #32/#33，任务卡 T-W0-009）**：
   - CI-1：ci.yml 聚合 `gate`（复用 CI-Workflows@v1 的 hygiene/check/dep-review
     + push 面 pip-audit + 宪法门禁 repo-gate），替代原 pr-check.yml（全部检查
     迁移并入，零削弱）；
   - SC-3：dependabot（github-actions + pip）+ automerge（App 身份，非 major
     自动合并）；
   - CI-4：zizmor.yml 豁免集中登记；gitleaks 全历史扫描配 .gitleaks.toml 白名单
     （仅 2 个合成测试常量，逐值核验非真实凭据）；
   - CG-2：.github/CODEOWNERS 基建路径显式归属 owner。
3. **平台侧配套（本 ADR 授权，一次性完成）**：
   - AG-4：AI_Web_School 挂载到 cloudbrid-agent 安装（App 可写仓）；
   - RL-1：production environment（required reviewer=owner + 仅受保护分支）。
4. **前置红灯修复随任务卡 T-W0-009 入库**：测试时间锚点动态化（修分区时间炸弹）、
   cryptography 49.0.0→50.0.0（PYSEC-2026-3552，依赖审计门禁清障）。
5. **语言栈存量豁免（范围限定）**：policy/languages.yaml application 层允许清单
   （go 默认 / typescript 限前端）面向**新服务选型**（flows.new_repo）；AI_Web_School
   为既有 Python 存量栈，不触发重写（languages.yaml language_change：语言选定后
   更换=重新立项）。若未来立项重写，走 flows.rewrite_project。
6. **nightly w2.sh 出口失败为存量问题**（playwright/E2E-1 演示步骤），不阻塞纳管：
   nightly 非 required check；失败建 issue 步骤已随本次补 issues:write 权限修复，
   红灯可见性恢复，修复另行任务。

## 后果

- AI_Web_School 的 PR 合并受 main-protection 约束（gate required + squash-only +
  线性历史），直推 main 将被 §8 检出；
- drift-check §1/§4/§7/§8/§9/§10 自下次运行起覆盖本仓；
- 依赖 major 升级留人、minor/patch 自动合并（SC-3），依赖审批走
  languages.yaml#dependency_policy；
- 本仓 constitution（specs/constitution.md）与组织治理基线并存：仓内铁律（三本账、
  校验门、PII 保险库等）继续有效，组织基线补齐的是仓库边界外的合并防线。
