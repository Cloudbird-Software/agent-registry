# ADR-0001: 建立 agent-registry，四类声明统一落盘

- status: accepted
- date: 2026-08-18
- deciders: 人（owner）+ AI

## 背景

多 agent 编排框架（openjiuwen）在本地运行，agent/技能/团队配置散落在运行目录，不可审计、不可版本化、无法跨机器复现。需要 single source of truth。

## 决策

1. 建立 `agent-registry` 仓（private），四类声明：`registry/{agents,skills,tools,teams}`，外加 `registry/models.yaml`。
2. 标准本体（JSON Schema，YAML 书写）放 `.github/standards/agent/`（tool/skill/agent/team/event 五个 schema）。
3. 层级规则：L0 标准（.github）→ L1 注册条目（本仓）→ L2 实现（各代码仓/openjiuwen 私有仓）→ L3 运行数据（数据库/对象存储）。上层只以 id 引用下层，不复制内容。
4. 技能载体沿用 openjiuwen 的 SKILL.md（frontmatter 声明 + Markdown 正文）：声明段管治理（检索/权限/验收），正文管执行，不做流程步骤结构化。
5. 状态门禁：注册条目 `status: proposed → approved` 必须走 PR；引用非 approved 条目 CI 拒绝（GOVERNANCE AR-2）。

## 后果

- 本地运行目录降级为部署产物：由 registry 渲染/同步生成，不是源。
- 换编排框架 = 重写 L2 渲染器，声明不动。
