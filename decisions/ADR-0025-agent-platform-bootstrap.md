# ADR-0025: agent-platform 立项——声明渲染到 openjiuwen 运行时的执行层

- status: accepted（2026-08-19）
- 关联: ADR-0002（LLM Gateway）、ADR-0010（原型/相位）、ADR-0011（team-collaboration v1）、ADR-0018（供应链清单）、ADR-0024（建仓先例）

## 背景

组织（一人软件公司）选定 openjiuwen 生态（openJiuwen-ai/jiuwenswarm 平台 +
openJiuwen-ai/agent-core SDK）作为声明式治理的落地运行时。此前尝试"直接下载上游
仓库自行配置"持续失败，根因（代码级确认）：

1. 源码安装需 Node/npm 构建前端 dist（不入 git）；
2. jiuwenswarm 以 `git+...@develop` 滚动依赖 agent-core，不可重现；
3. 重二进制依赖（chromadb/pgvector/faiss）与 config.yaml 占位符耦合。

## 决策

### 1. 新建 L2 仓 `Cloudbird-Software/agent-platform`

从 template-service 派生（flows.new_repo，照 ADR-0024 先例）。职责：

- **渲染器**：agent-registry 声明（agents/teams/models/schemas/standards）→
  jiuwenswarm workspace/config（幂等、带指纹、可 diff）；
- **workflow 编译器**：team-collaboration 相位图 + steps → SwarmFlow
  （agent_teams/workflow 确定性引擎）脚本——编排权在机制不在 LLM；
- **机制原型执行面**：card-gate/预算/写锁/事件哈希链等 11 个机制的可执行实现；
- **TUI 可观测 + agentctl 干预命令**（owner 要求：可看、可干预、可被 agent 调用）；
- **漂移监控**：渲染产物 ↔ 声明 一致性检查，CI 门禁化。

registry 保持纯声明（L1 不动）；agent-platform 是其唯一渲染消费者。

### 2. 上游消费策略：零 fork、零 submodule、PyPI wheel 钉版

- `jiuwenswarm==0.2.3`（wheel 含预构建前端 dist，规避根因 1）
- `openjiuwen==0.1.16.post6`（PyPI wheel，已验证含 SwarmFlow 引擎 31 模块）
- 显式覆盖 jiuwenswarm 的 `git@develop` 依赖（先装 openjiuwen 再装平台，规避根因 2）
- 重二进制依赖全部由 Docker 基础镜像预装（规避根因 3）
- 定制只走上层扩展点（extensions/AgentBackend/rails/MCP/config），升级=改 lock 走 PR

### 3. 供应链登记（本 ADR 随附执行）

- projects.yaml：jiuwenswarm license 回填 Apache-2.0（首审动作）；新增
  openJiuwen-ai/agent-core 条目（Apache-2.0，deploy-time-pin，osv-scanner 周审）；
- models.yaml：gateway 增 `sdk_runtime: {repo: openJiuwen-ai/agent-core,
  policy: deploy-time-pin}`（upstream_runtime 指平台，sdk_runtime 指内核 SDK——
  双上游显式化）；
- validate.py：消费者集合纳入 sdk_runtime.repo（与数据同源演进，ADR-0011 先例）。

### 4. 语言政策联动（另行 .github PR，本 ADR 为依据）

agent-platform 为 Python 仓（openjiuwen SDK 为 Python，不写 Python 无法落地——
声明适配现实的显式修订）。languages.yaml application 层增
`{language: python, when: "agent-runtime integration (agent-platform)"}`，
配套 PY-* gate 规则（ruff/pytest/uv lock）。

### 5. 平台配套（owner 已随本 ADR 执行）

squash-only、删分支、main 保护（required: gate 及其依赖）、CODEOWNERS owner-only
——照 ADR-0024 Use-up-Plan 先例。建仓 bootstrap commit 直推豁免逐 SHA 登记
（.github PR 随附）。

## 后果

- agent-platform 自首个 PR 起受 main-protection 约束；其 CI 含渲染漂移门禁
  （声明变更必须伴随渲染产物同步，或显式标记 pending-render）；
- 上游升级（月度/按需）：bump lock → MockBackend dry-run + 场景断言重放 → PR；
- 对上游的通用性改进（如 worker 白名单可配置化）优先回馈上游 PR，compat 层
  集中单模块且带版本守卫；
- 本 ADR 不改变 registry 门禁（validate/simulate-wave 双 required 维持）。
