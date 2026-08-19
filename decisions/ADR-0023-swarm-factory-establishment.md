# ADR-0023: swarm-factory 平台仓建立——声明规定落地 openjiuwen 的工程载体

- 状态：approved
- 日期：2026-08-19
- 决策人：owner（randypanding）
- 关联：ADR-0002（LLM Gateway，rev1 上游策略）、ADR-0018（供应链/上下文装配）、ADR-0014（intent-routing）、ADR-0015（场景引擎）

## 背景与动机

本仓（agent-registry）是组织智能体声明的 single source of truth，但声明只规定
"应该是什么"。一人公司要运转，必须把声明落到一个真实的多智能体运行时上。
选型结论（2026-08-19 完成三仓调研）：

- **底座 = openJiuwen-ai/JiuwenSwarm**（多智能体 swarm 运行时；agent 身份即文件
  [IDENTITY/SOUL/config]，与声明式注册表同构；单机 inprocess 零外部服务）。
- agent-studio 是重中间件可视化管理台（Java+Angular+MySQL/Redis/MinIO，官方文档
  明言不含 swarm 编排内核），不作底座；deepsearch 是搜索专精应用，不是通用底座。

既往"下载仓库后配不起来"的根因诊断：源码安装需 npm 构建前端；核心依赖
`openjiuwen` 从 gitcode develop 分支动态拉取（移动目标）；分布式 Team 依赖
PostgreSQL+A2X 外部服务；Python 版本窗口 3.11–3.13。

## 决策

1. **新开工程仓 `Cloudbird-Software/swarm-factory`**（本仓声明体系中的"平台仓"），
   承担声明→运行时的翻译与机制服务。本仓保持纯声明 SoT，不混入实现。
2. **上游以制品形式消费，不 fork、不 submodule**（延续 ADR-0002 rev1）：
   - 钉版 `jiuwenswarm==0.2.3`（PyPI；git tag `release_0.2.3` 作哨兵锚点）；
   - `openjiuwen` 锁定 PyPI 发布版，覆盖其 develop 分支移动引用；
   - 升级回路：weekly 比对 PyPI → 维护卡提案（maintain_loop，pre_approved：
     哨兵+渲染 golden+冒烟全绿才并）；临时补丁目录 `patches/` 目标恒为空。
3. **组织代码只写在上游稳定扩展面上**：`extensions.extension_dirs` 扩展包、
   hooks 退出码契约（0=继续/2=阻断）、MCP stdio 协议、config.yaml schema。
   CI 渲染哨兵（tests/sentinel.py）对钉版 tag 比对四面：config 段集合 /
   HookEvent 枚举 / 扩展机制 / 退出码注释——上游破坏性变更在我们 CI 红灯。
4. **渲染管线**：`registry-sync` 从本仓钉版声明渲染 JiuwenSwarm 运行时工件
   （agents/modes.team/permissions/hooks/mcp 六段 config 覆盖 + IDENTITY/SOUL/
   skills/schemas/波次模板/执法规则/装配清单）。entrypoint 与 CI 双强制点：
   **先跑本仓 validate.py + simulate-wave.py，未过审拒绝渲染**。渲染产物受
   golden 差分守护，手改=违规。
5. **语言例外**：swarm-factory 语言随上游 openjiuwen 保持中文（上游文档/注释/
   配置以中文为主），不遵循组织其他仓的英文倾向。本决定为 owner 拍板的
   组织语言规则显式例外，仅适用于该仓。
6. **开箱即用**：`cp .env.example .env`（3 必填项：API_BASE/API_KEY/
   MODEL_PROVIDER）→ `make up`。无 npm、无 gitcode 直连、无 PostgreSQL/A2X；
   LLM 接入双路线：直连 provider（起步）或 LLM Gateway per-team key（正式）。

## 落地映射（声明 → 载体）

| 声明 | 载体（swarm-factory 内） |
|---|---|
| registry/agents+identities+skills | config.agents 段 + IDENTITY/SOUL 物化 + skills 目录 |
| registry/teams | config.modes.team.*（ephemeral→temporary；inprocess） |
| capabilities.allow / permissions.overrides | capability gate hook（PreToolUse，exit 2 阻断） |
| guardrails.forbidden（可执法子集） | 全局硬阻断规则；不可执法项进装配注记（不假装执法） |
| io_contract（schemas/*.json） | io_contract rail（SwarmFlow schema 前线 + 独立终检 CLI） |
| flow.phases（五相位） | waves/delivery_wave.py（SwarmFlow 模板；HITL=非委派点） |
| flows.event_integrity | event-sink 哈希链账本（tool_called 由平台钩子落账） |
| check:intent-ratified | card-gate 开卡前置（exit 非 0=不开卡） |
| lifecycle（ephemeral/handoff/memory_digest） | team-lifecycle（digest 先于销毁，契约校验） |
| intent-routing 八分类 | intent-gateway（声明表驱动，歧义取重侧+确认） |
| observability 六视图 | attention-view（只读投影；budget 计量诚实指向 Gateway） |
| context-assembly | manifest.json（组件序+version_read 指纹） |

## 后果

- 正面：声明获得真实执行面；上游更新=改一行钉版+哨兵验证；一人运维负担最小
  （单容器+可选 gateway）；既往配置耦合问题被镜像固化消灭。
- 负面/代价：per-agent 差异化执法当前为组合近似（hooks 全局硬防线+SwarmFlow
  schema+IDENTITY），完整 per-session 凭据收窄留待 P3；事件账本 OTLP
  protobuf 面未接（hooks JSON 侧车替代）。
- 边界：swarm-factory 为 org-internal 资产，按 projects.yaml 边界规则不入开源
  清单；本 ADR 随同 projects.yaml 的 jiuwenswarm license 首审回填（Apache-2.0，
  证据：上游 LICENSE 文件与 pyproject license 声明）一并生效。
