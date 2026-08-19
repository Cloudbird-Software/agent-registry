# ADR-0027: mutual 立项——LLM 双向互惠推荐引擎的 Go+BAML 重写

- status: accepted（2026-08-20）
- 关联: ADR-0021（bootstrap 直推豁免机制）、ADR-0023（存量栈语言豁免先例）、ADR-0024（建仓申报先例）、ADR-0025（语言政策声明适配先例）

## 背景

mutual 于 2026-08-19 由 owner 从 template-service 派生创建（GitHub 建仓
initial commit `f5d9b5b58d4dc30a2b0e259449862fc4a3c91f6b`，建仓时序上
分支/PR 尚不存在，属 ADR-0021 (b) 类建仓 bootstrap 直推）。该仓未申报入
governance/REPOS.yaml，被 drift-check §7b/§8 检出。

项目来源：owner 在 gitcode.com/feasylol/mutual 维护的 LLM 双向互惠推荐引擎
（Python 存量实现，约 9k LOC，spec 驱动：11 阶段流水线
extract→hyde→embed→similarity→select→score→pre_matrix→match→introduce→report→evaluate，
NSW 匹配 + envy-freeness 公平性校验，HR@K/NDCG@5 评测门禁，golden fixtures
齐备）。owner 决策：将其落进组织并按 policy/languages.yaml 以 Go+BAML 重写
——"深接口、强类型、结构清晰、AI 阅读友好"为重写第一目标。

## 决策

1. **申报入图**：REPOS.yaml 增 mutual 条目——layer L2、visibility public、
   status active；角色：产品仓——LLM 双向互惠推荐引擎（Go+BAML 重写，源自
   gitcode.com/feasylol/mutual 存量 Python 项目）。
2. **直推豁免登记**：expected-state.json direct_push_exemptions 增 mutual
   条目，逐完整 SHA 登记 `f5d9b5b58d4dc30a2b0e259449862fc4a3c91f6b`
   （ADR-0021 (b) 建仓 bootstrap 类）。
3. **语言路线（无需 languages.yaml 修订）**：Go 为 application 层默认语言；
   BAML 为 llm_prompt 层允许语言（类型化 prompt 契约，BAML-1 golden test
   gate）。Python 存量基线按 ADR-0023 AI_Web_School 先例做一次性存量导入
   豁免——仅作为重写参照系与 golden fixtures 来源（R-06 不可逆固化），重写
   PR 合并后 Python 代码面即移除，不构成长期语言栈。
4. **新增依赖提案（languages.yaml dependency_policy proposal_format，owner
   随本 ADR 批准）**：
   - 名称：`github.com/boundaryml/baml/go`（BAML Go runtime）
   - 用途：BAML 生成客户端的运行时——LLM prompt 类型化契约、结构化输出
     解析与校验重试闭环
   - 许可证：Apache-2.0（上游仓库 LICENSE 实证；不在 forbidden_licenses）
   - 标准库可否替代：不可——类型化 prompt 契约（schema→渲染→解析→校验）
     为 BAML 核心能力，标准库无等价物；手写替代将退化为字符串拼接 prompt
     （llm_prompt 层 forbidden 项 prompt_string_interpolation_in_code）
5. **平台配套（已随本 ADR 执行）**：new-repo-init 全步骤——squash-only/
   删分支/auto-merge/wiki+projects 关闭、production environment（RL-1）、
   cloudbrid-agent 安装挂载（AG-4）；gate/automerge/scorecard/CODEOWNERS/
   dependabot 由 template-service 派生自动继承（CI-1/CI-4/SC-3/CG-2）。
6. **重写流程（GOVERNANCE flows.rewrite_project）**：存量 golden fixtures
   随 Python 基线导入先行固化（不可逆，R-06）；骨架 PR 先行（目录+边界
   lint+空实现，CI-1）；模块 PR 各带契约测试；golden 逐位回归作为新旧实现
   的差分门禁（T-09 精神——期望值不因实现变更而改动）；BAML-1 自重写首个
   PR 起生效。

## 后果

- drift-check §7b（未申报）与 §8（直推）对 mutual 的漂移消除；
- mutual 自首个 PR 起受 main-protection（gate required）约束，直推将再次
  被检出且无新增豁免通道；
- Python 基线为显式过渡态：存在仅限重写周期，重写合并后 Python 代码面
  移除，仓库语言面收敛为 Go+BAML；
- 对外接口与门禁数值变更走 CHANGELOG.md（Conventional Commits）。
