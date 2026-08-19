# ADR-0019: agent-registry 仓库可见性修正为 public

- status: accepted
- date: 2026-08-19

## 背景

组织惯例是全公开仓库：`flows.new_repo` 建仓命令即 `gh repo create --public`（GOVERNANCE.yaml），组织其余 5 仓（.github / CI-Workflows / template-service / AI_Web_School / Shorts_Director）全部 public，supply_chain 政策注释亦以"公开仓库"为前提。

但 `.github/governance/REPOS.yaml`（GM-4 组织地图，drift-check §7a 的期望状态真源）将 agent-registry 申报为 `visibility: private`——与组织惯例相悖的申报。后果：owner 手动改为 public 后，2026-08-19 03:49 UTC 的 governance-drift 运行即按错误期望状态报漂移（实际 public vs 期望 private）。

排查确认（诚实记录）：

- drift-check.sh 为纯只读检测（开 issue 报警）；apply.sh 仅 PATCH 合并策略（squash/delete_branch），不写可见性——**组织内无自动改回可见性的流程**。"被改回私有"的确切动作来源无法从代码与可及的审计接口确认。
- 但错误期望状态是真问题：不修正申报，任何一次改 public 都会被每日 drift 检测报为漂移。

## 决策

1. agent-registry 可见性改为 **public**（本 ADR + `.github` 仓 REPOS.yaml 申报修正 PR 同步执行）。
2. 组织"全公开仓库"从惯例升为明示政策：新仓一律 public（flows.new_repo 已是如此）；如未来确需私有仓，须在 REPOS.yaml 标 `exempt` 并注明理由（GM-4 既有机制）。

## 公开前核查

- 本仓无明文密钥：全部 `env:` 引用（AGENTS.md 硬规则）；`deploy/llm-gateway/.env.example` 仅占位符；git grep 密钥模式零命中。
- 公开使 `.github` gate.yml adr-required 注释中"agent-registry 是私有仓"的前提失效——该注释解释的存在性后验设计（drift-check §10）仍然有效，无破坏；跨仓读变为可行是未来简化空间，非必需。

## 后果

- drift-check §7a 转绿（实际 public = 期望 public）。
- `check:*` 依赖本仓 standards/ 引用的外部消费方（CI-Workflows / template_service）跨仓读取不再受私有仓权限限制。
- 攻击面扩大评估：本仓为声明层（YAML/MD/校验器），无运行时凭据；供应链审计（ADR-0018 projects.yaml）已就位。
