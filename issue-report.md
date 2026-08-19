# 治理体系红队测试报告：流程断点、角色失效与反馈死循环

本报告基于对 Cloudbird-Software 三个治理仓库（agent-registry、Cl-Workflows、.github）的深度分析，通过 30 个极端场景的红队测试，发现治理体系在真实开发流程中可能遇到的流程断点、角色无法触发、任务无人认领、反馈死循环等问题。

---

## 一、流程断点与死锁

### 1.1 owner 不可用导致全局停滞

**问题位置：**
- `standards/attention-ledger.yaml:13-16` - intent_ratification 声明为 synchronous
- `standards/flows.yaml:13-14` - 未批准意图不得开卡

**问题描述：**
当 owner 因故（休假/疾病/失联）长期不可用时，所有新意图在 intent_ratification 阶段永久阻塞。intent_ratification 被声明为 synchronous 阻塞点，无超时降级机制。与 normative amendment 不同（后者有 24h 默认动作），intent_ratification 没有超时后的自动处理路径。

**影响：**
- 3 个波次同时运行时，超过 attention-ledger 的 max_synchronous_per_week: 2 硬上限
- judge 无法处理 intent_ratification 的升级（这是 non_delegable）
- maintenance_wave 的 trigger 可触发但执行仍受阻塞
- 系统进入全局等待态，无自动恢复路径

### 1.2 planner 退场与 handoff 执行者的声明矛盾

**问题位置：**
- `standards/team-collaboration.yaml:97-98` - planner.exit_on: cards.ratified
- `standards/team-collaboration.yaml:193` - memory-export by seat:planner + seat:test_author
- `standards/context-assembly.yaml:90` - memory.digest.producer: handoff 相位在场座位

**问题描述：**
planner 的 exit_on 是 cards.ratified，意味着 planner 在 plan 相位结束后就退场了。但 handoff 相位的 team_side 项中，memory-export 声明由 seat:planner + seat:test_author 共同执行。planner 在 handoff 相位已退场（state=exited），但被声明为 memory-export 的执行者。

**影响：**
- 如果 planner 实例失效或已退场，memory-export 无法完成
- destroy 条件要求 after-handoff(team_side)，memory-export 未完成则队永远不销毁
- ephemeral 队的生命周期断裂，workspace 和资源永久占用
- 4 项 team_side handoff 中，memory-export 是唯一没有备选执行者的项

### 1.3 planner.state==exited 是波次级阻塞

**问题位置：**
- `standards/team-collaboration.yaml:252` - plan→build when: cards.ratified AND planner.state == exited
- `standards/team-collaboration.yaml:97` - planner.reentry: on_normative_amendment

**问题描述：**
planner.state 是座位级状态，不是卡级状态。当波次中部分卡需要 normative amendment（planner 重入，state=active）时，planner 无法 exit，所有已 ratified 的卡也无法进入 build 相位。

**影响：**
- 已 ratified 的卡等待 planner exit，但 planner 因其他卡的重入而无法 exit
- 单卡 amendment 阻塞所有已 ratified 卡
- 这是串行化瓶颈，不是死循环但导致波次进度停滞

### 1.4 波次冻结后解冻完全依赖 owner

**问题位置：**
- `standards/team-collaboration.yaml:322` - escalate_when: 同波次 > 3 → 冻结新开卡+escalate owner
- `standards/team-collaboration.yaml:322` - 是否整波回炉由 owner 裁——不自动

**问题描述：**
当 planner 产卡质量持续低下（如连续 10 张卡触发 normative amendment），波次会被自动冻结。但解冻需要 owner 裁决"是否整波回炉"，judge 无法介入此决策。

**影响：**
- owner 不可用时，冻结的波次永久冻结
- 10 张卡 × 每张 2 次 normative amendment = 20 次 owner 审批
- 日批窗口设计为批量处理，但集中到达时超出 owner 单日处理能力
- amendment_rate 指标需要 min_sample=10 才触发自动动作，前 10 次只能依赖 owner 人工干预

---

## 二、角色无法触发与任务无人认领

### 2.1 judge 激活条件与族独立性冲突

**问题位置：**
- `standards/team-collaboration.yaml:436` - judge_service activation: 僵持累计 >= 2
- `standards/team-collaboration.yaml:141` - independence: 族 ≠ 争议双方
- `standards/team-collaboration.yaml:442` - degraded_mode: 可用族数 < 激活中的独立性需求

**问题描述：**
当 sovereign-family 模型族不可用时，judge 被迫降级到 flagship-family（与 test-author 同族）或 flash-family（与 builder 同族）。degraded_mode 有声明但无具体执行路径——当族数不足时，judge 无法激活，升级只能直达 owner。

**影响：**
- degraded_mode 是纯声明，无执行体阻止 judge 激活
- validate.py 只校验 models.yaml 中的静态 family 映射，不校验运行时实际模型
- LLM Gateway 的 failover 可能静默路由到其他族
- 没有运行时检查验证"当前 judge 实例的实际模型族 ≠ 争议双方的模型族"

### 2.2 builder 写 tests/acceptance/ 的防线间隙

**问题位置：**
- `standards/checks.yaml:38-41` - check:pr-identity-path-matrix status: planned
- `registry/agents/backend-dev.yaml:25` - permissions.overrides 仅拦截 write_file
- `standards/archetype-profiles.yaml:61` - enforced_by: [token-path-scope, check:pr-identity-path-matrix]

**问题描述：**
check:pr-identity-path-matrix 状态为 planned（未实装），permissions.overrides 仅拦截 write_file 工具的 tests/acceptance/** 路径。builder 可以通过 bash 工具（shell_sandbox 能力）执行文件写操作绕过拦截。token-path-scope 是被引用但未定义的概念性机制。

**影响：**
- bash 工具不在 write_file 的拦截范围内
- PR 层面的身份×路径矩阵检查未实装
- CT-BLD-001 控制测试期望"令牌路径拒绝 + pr-identity-path-matrix check 失败"，但两者都未完全实装
- builder 可以通过 shell 命令写入 tests/acceptance/ 路径

### 2.3 curator 修改 standards/ 的防线依赖平台配置

**问题位置：**
- `registry/agents/curator-main.yaml:16` - allow 包含 fs_write_repo
- `CODEOWNERS:8` - /standards/** @randypanding
- `standards/control-tests.yaml:134-142` - CT-CUR-002 runtime: manual_only

**问题描述：**
curator 拥有 fs_write_repo 能力，可以修改 standards/ 文件。CODEOWNERS 声明了 owner 审查要求，但这依赖 GitHub 仓库的 ruleset 开启 "require code-owner review"。此配置在 GitHub 平台侧，不在本仓声明层可验证范围内。

**影响：**
- curator 的 permissions.overrides 不覆盖 standards/ 路径
- CODEOWNERS 的强制力取决于 GitHub 平台侧 ruleset 配置
- curator 可以创建 ADR 草案并引用它，通过 adr-required 检查
- CT-CUR-002 是 manual_only 运行时，自动化管线不验证此防线

### 2.4 responder 的 ci_trigger 可能成为间接前进部署通道

**问题位置：**
- `registry/agents/responder.yaml:17` - allow 包含 ci_trigger
- `standards/team-collaboration.yaml:220` - forward_fix: owner_required
- `registry/agents/responder.yaml:34` - forbidden: [no-forward-deploy]

**问题描述：**
responder 的 allow 列表不含 deploy_forward，但包含 ci_trigger。如果 CI 流水线包含部署步骤（如 release-bot 的 pipeline），responder 可能间接触发前进部署。forward_fix: owner_required 是策略声明，没有对应的 check:* 防线强制执行。

**影响：**
- ci_trigger 能力可能成为间接前进部署的通道
- forward_fix: owner_required 是策略声明，无代码强制
- deployer 在 incident_cell 中的存在为角色混淆提供了可能
- forbidden 列表依赖 LLM 遵守，非代码级拦截

### 2.5 ephemeral 队销毁时 handoff 执行者缺失

**问题位置：**
- `standards/team-collaboration.yaml:193` - memory-export by seat:planner + seat:test_author
- `standards/team-collaboration.yaml:97` - planner.exit_on: cards.ratified
- `standards/team-collaboration.yaml:197` - destroy: after-handoff(team_side)

**问题描述：**
planner 在 handoff 相位已退场（exit_on: cards.ratified），但 memory-export 声明需要 planner 执行。如果 planner 实例失效，memory-export 无法完成，destroy 条件永不满足，队永远不销毁。

**影响：**
- 4 项 team_side handoff 中，memory-export 是唯一没有备选执行者的项
- 队会永远不销毁，workspace 和资源永久占用
- handoff 没有 TTL（incident_cell 有 72h TTL，但 delivery_squad 没有）
- 没有超时或降级机制

---

## 三、反馈死循环与预算耗尽

### 3.1 amendment 循环与 overhead_pool 耗尽

**问题位置：**
- `standards/team-collaboration.yaml:322` - escalate_when: 同一卡 normative amendment >= 2
- `standards/team-collaboration.yaml:97` - planner.reentry: on_normative_amendment
- `standards/team-collaboration.yaml:399` - escalation 与 judge 调用永不受任何预算约束

**问题描述：**
planner 连续产出需要 normative amendment 的卡，每次 planner 重入后仍然产出歧义的卡。escalate_when 阈值设置不合理（第 2 次就 escalate），escalate 到 owner 后 owner 如何处理未定义。planner 重入无次数限制，overhead_pool 会被耗尽但升级通道"永不冻结"的不变式在物理层被违反。

**影响：**
- escalate 到 owner 后，owner 的响应路径未闭环
- planner 产卡质量问题的归因机制存在但无强制约束
- overhead_pool 耗尽后，escalation 通道虽然"不冻结"，但执行者已无预算可用
- 不变式在物理层被违反

### 3.2 backlog 无限堆积与 curator 单点瓶颈

**问题位置：**
- `standards/team-collaboration.yaml:362` - producer_gate: planner 组建波次必处置 top-k
- `standards/flows.yaml:78-79` - deferred: 唯一豁免出口
- `standards/team-collaboration.yaml:201` - stewardship.topology: single-seat

**问题描述：**
escape review 持续产出 backlog 提案，curator 归并速率 < 提案产生速率，backlog 累积到 100 条以上。curator 是单座位，归并速率受限于处理能力。producer_gate 的 top-k 处置无时间窗约束，deferred 条件的机器可判定性未强制校验。

**影响：**
- backlog 堆积无上限报警
- curator 单点瓶颈，缺席时归并完全停滞
- deferred 条件可能成为滥用出口
- 堆积会导致后续维护波次的预算压力激增

### 3.3 budget 熔断后队无法恢复

**问题位置：**
- `standards/team-collaboration.yaml:395` - team_envelope: usd+wall_clock 硬熔断
- `registry/teams/dev-wave.yaml:56-58` - team_envelope: {usd: env:TEAM_USD_CAP, wall_clock: env:TEAM_WALL_CLOCK}
- `standards/flows.yaml:57` - budget.on_exceed: fail-closed

**问题描述：**
team_envelope 预算耗尽后队被冻结，但预算追加路径未声明。owner 如何追加预算？修改 env:TEAM_USD_CAP？冻结期间的卡状态未定义（paused 还是 frozen？）。wall_clock 耗尽不可恢复（时间无法追加）。

**影响：**
- 预算追加路径未声明
- 冻结期间的卡状态未定义
- wall_clock 耗尽不可恢复
- 冻结期间的 handoff 无法完成，队永远无法销毁
- escalation 到 owner 后无 SLA

### 3.4 judge 判决被推翻后的循环

**问题位置：**
- `standards/archetype-profiles.yaml:155` - reversible_by=owner
- `standards/team-collaboration.yaml:135` - judge.kind: llm_service, per_dispute
- `standards/team-collaboration.yaml:436` - judge_service activation: 僵持累计 >= 2

**问题描述：**
judge 做出判决后被 owner 推翻，争议双方继续僵持。推翻后再次激活 judge 的路径未定义（僵持计数器是否重置？）。判例污染风险（被推翻的判决是否入库？）。judge 实例销毁后无法复用（同一 dispute 不得复用上次实例）。

**影响：**
- 推翻后再次激活 judge 的路径未定义
- 判例污染风险
- owner 推翻判决后无强制要求给出替代方案
- verdict_stalemate 事件可能重复产出，形成死循环

### 3.5 maintenance_wave 无完成条件

**问题位置：**
- `standards/flows.yaml:83` - trigger: backlog 存在 security 级条目 OR aging 最老条目 > 30d
- `standards/flows.yaml:84` - executor: delivery_squad 以 backlog 为波次范围组建
- `standards/flows.yaml:86` - metrics: [backlog_aging_p50/p95, deferred_count, maintenance_wave_count]

**问题描述：**
维护波次处理 backlog 时，escape review 持续产出新提案。维护波次无完成条件，波次范围不断扩大，导致波次永远无法完成。aging 指标的单调性未保证（新提案 aging 为 0 会拉低 p50/p95）。

**影响：**
- 维护波次无完成条件
- aging 指标的单调性未保证
- 维护波次与正常波次的资源竞争
- escape review 的产出速率无上限

### 3.6 owner 控制动词冲突

**问题位置：**
- `standards/flows.yaml:88-118` - owner_control
- `standards/team-collaboration.yaml:302-309` - card.lifecycle.states

**问题描述：**
owner 在 TUI 上同时点击 pause 和 abort，两个事件几乎同时到达。控制动词的原子性未声明，状态转移的冲突未定义（pause 要求进入 paused，abort 要求进入 aborted）。事件的顺序依赖未声明。

**影响：**
- 控制动词的原子性未声明
- 状态转移的冲突未定义
- interface-gateway 的并发控制未声明
- TUI 的并发控制未声明

### 3.7 release_bot 部署失败后重试循环

**问题位置：**
- `standards/team-collaboration.yaml:156` - stall_escalation: 流水线停滞超时 → escalation
- `standards/archetype-profiles.yaml:410` - stall_escalation: 流水线停滞超时 → escalation

**问题描述：**
release_bot 部署 behind flag 失败，流水线重试但每次都失败。停滞超时未声明具体值（1 小时？24 小时？）。escalation 后的处理未定义（escalation 到谁？owner 还是队内成员？）。重试次数未限制。

**影响：**
- 停滞超时未声明具体值
- escalation 后的处理未定义
- 重试次数未限制
- release_bot 失败后无自动通知 owner 的机制
- 卡的状态未定义（停留在 integrate 还是进入 handoff？）

### 3.8 incident_cell TTL 到期后 owner 不响应

**问题位置：**
- `standards/team-collaboration.yaml:232` - on_ttl_expiry: escalate_to_owner + extension_requires_owner
- `registry/teams/incident-cell.yaml:56` - on_ttl_expiry: escalate_to_owner + extension_requires_owner
- `standards/attention-ledger.yaml:39` - incident_ttl_expiry default: 延长需 owner 主动批准

**问题描述：**
sev1 事故 incident_cell 实例化，72h TTL 到期，owner 不响应升级。escalate_to_owner 的具体动作未定义（发通知？产事件？重复频率？）。extension_requires_owner 的执行者未定义。冻结期间的资源消耗未声明。

**影响：**
- escalate_to_owner 的具体动作未定义
- extension_requires_owner 的执行者未定义
- 冻结期间的资源消耗未声明
- owner 不响应 escalation 时无二次升级机制
- "持续升级提醒"的频率和方式未定义

---

## 四、基础设施故障与单点故障

### 4.1 LLM Gateway 完全不可用

**问题位置：**
- `standards/archetype-profiles.yaml:376` - scheduler.llm_assist: {stage: failure-triage}
- `standards/archetype-profiles.yaml:384` - interface-gateway.llm_assist: {stage: nl-to-intent}
- `standards/archetype-profiles.yaml:391` - metrics-aggregator.llm_assist: {stage: anomaly-narrative}

**问题描述：**
LLM Gateway 服务宕机，所有 LLM 原型无法工作。虽然机制原型（verifier, integrator, release_bot, card_gate）本身无 LLM 主体，但 scheduler 的 failure-triage、interface-gateway 的 NL→intent 解析、metrics-aggregator 的异常叙述均声明了 llm_assist 依赖。这些"薄 LLM 层"的失败可能阻塞机制原型的完整功能。

**影响：**
- 机制原型依赖 LLM assist 的隐性耦合
- degraded_mode 只处理"族不足"但不处理"全部不可用"
- 队冻结后无超时自动销毁或通知 owner 的机制
- 机制原型可独立工作但无法接收新任务

### 4.2 数据层完全丢失

**问题位置：**
- `standards/context-assembly.yaml:92-93` - memory.digest.ordering_invariant: 不随 30d 轨迹清理
- `standards/flows.yaml:47` - 存储 append-only + 哈希链
- `standards/team-collaboration.yaml:53-54` - artifact_mediated.medium: 数据层

**问题描述：**
数据库故障，事件流、backlog、cards 全部丢失。memory_digest 的"不随 30d 清理"依赖数据层存活，该声明只防清理不防灾难。事件流 append-only + 哈希链保证完整性但不保证可用性。跨生命周期接口完全依赖数据层。

**影响：**
- memory_digest 的持久性保证只针对"30d 清理"，不针对存储灾难
- 事件流哈希链保证完整性但不保证可用性
- 跨生命周期接口完全依赖数据层
- 无 RPO/RTO 声明
- 无数据层备份/恢复流程声明
- 在途卡的工作全部丢失，无重建机制

### 4.3 所有模型族都不可用

**问题位置：**
- `standards/team-collaboration.yaml:442` - degraded_mode: 可用族数 < 激活中的独立性需求
- `registry/models.yaml:16/23/37/44` - 只有 3 个 LLM 族 + 1 个 embed 族
- `standards/archetype-profiles.yaml:166` - judge.independence: distinct_model_family_from: [builder, test-author]

**问题描述：**
flash-family, flagship-family, sovereign-family 全部宕机。degraded_mode 的触发条件可达成但行为未定义（可用族数 = 0 时动态排无意义）。模型注册表只有 3 个 LLM 族，无第四族后备。judge 的族独立性要求无法降级。

**影响：**
- degraded_mode 无"全部不可用"终态
- 模型注册表只有 3 个 LLM 族，无后备
- judge 的族独立性要求无法降级
- owner 注意力账本未预留"全系统冻结时的处理容量"
- 无自动通知 owner 的机制

### 4.4 supply chain 攻击

**问题位置：**
- `standards/checks.yaml:78-83` - check:supply-audit status: planned
- `registry/projects.yaml:24` - license: unverified
- `registry/projects.yaml:25` - pin_policy: deploy-time-pin
- `registry/models.yaml:12` - upstream_runtime: 官方镜像，不 fork 不 submodule

**问题描述：**
openJiuwen-ai/jiuwenswarm 被投毒。supply-audit check 状态为 planned，未实装。license 字段为 unverified。pin_policy 为 deploy-time-pin 但无 hash 钉扎（tag 级钉扎可被强制推送覆盖）。不 fork 不 submodule 策略意味着组织直接依赖上游的完整性。

**影响：**
- supply-audit 未实装意味着投毒检测能力为零
- license 永远未回填
- deploy-time-pin 的具体机制未在声明层定义
- maintain_loop 无输入源
- 无供应链事件的 incident 响应流程

### 4.5 interface-gateway 无法结构化 intent

**问题位置：**
- `standards/team-collaboration.yaml:113-119` - interface_gateway: organization-level
- `standards/intent-routing.yaml:95` - classifier: interface-gateway
- `standards/intent-routing.yaml:10-11` - R2: owner 从不"启动"任何东西

**问题描述：**
interface-gateway 的 NL→intent 解析失败，所有 owner 意图无法被结构化。interface-gateway 是唯一的意图入口，无备选入口。intent-routing 的 classifier 完全依赖 interface-gateway。owner 无直接提交结构化意图的通道。

**影响：**
- interface-gateway 是组织级单点
- 无 owner 直接提交结构化 intent 的旁路
- 无手动路由机制
- incident_cell 的 owner 呼叫触发源也依赖 interface-gateway
- TUI 控制动词也经 interface-gateway 转发

### 4.6 scheduler 状态机卡死

**问题位置：**
- `standards/archetype-profiles.yaml:372-378` - scheduler.kind: mechanism
- `standards/flows.yaml:88-118` - owner_control 只覆盖卡级
- `standards/team-collaboration.yaml:259` - deadlock_check: 每 phase 存在可达 exit 边

**问题描述：**
scheduler 状态机进入非法状态，无法分派新卡，无法推进现有卡。scheduler 是机制原型但无手动重置声明。owner 控制动词只覆盖卡级，不覆盖 scheduler 状态。wave.frozen 是 builder 退场条件，但整波冻结后如何解冻未声明。

**影响：**
- 无 scheduler 状态机手动重置机制
- owner 控制动词不覆盖 scheduler 状态
- 波级冻结无解冻路径
- 无"跳过 scheduler 直接分派"的旁路
- 无 scheduler 状态快照与回滚机制

### 4.7 verifier 持续误判

**问题位置：**
- `standards/archetype-profiles.yaml:345-354` - verifier.kind: mechanism, llm_assist: none
- `standards/archetype-profiles.yaml:74` - mutation score 归因 test-author
- `standards/flows.yaml:30-39` - escape_review trigger: owner 或生产发现

**问题描述：**
verifier 对所有 PR 都判 fail。verifier 是纯机制原型，误判意味着 CI 环境本身有问题。mutation score 可发现 test_author 的问题但非 verifier 的问题。escape review 依赖 owner 或生产发现，但 verifier 持续 fail = 无 PR 能通过 gate = 无代码能合并 = 无生产缺陷可 escape。

**影响：**
- 无 verifier 判决正确性的独立校验机制
- mutation score 归因 test_author 不归因 verifier
- escape review 无法在"无代码能合并"的场景下触发
- 无"verifier 旁路"或"人工覆盖 verifier"机制
- builder 和 test_author 均无法修正 verifier 的误判

### 4.8 curator 单点瓶颈

**问题位置：**
- `standards/team-collaboration.yaml:199-202` - stewardship.topology: single-seat
- `standards/team-collaboration.yaml:195-196` - stewardship_side: [memory-distill, adr-write]
- `standards/archetype-profiles.yaml:189` - curator.kind: llm

**问题描述：**
多个 ephemeral 队同时完成发布进入 handoff，stewardship 无法同时处理。handoff 的 stewardship_side 只有 curator 一个座位。curator 是 LLM 原型，处理速度受 LLM 响应时间约束。

**影响：**
- curator 是 stewardship 的单座执行者
- 无 handoff 排队机制
- 无 curator 的并发扩展机制
- 队销毁不等待 stewardship_side，但 memory-distill 延迟不影响销毁
- 若 curator 因 LLM Gateway 问题无法工作，handoff 素材堆积无处理

### 4.9 owner 凭据泄露

**问题位置：**
- `standards/archetype-profiles.yaml:441` - drift-check §9 对账 admin 唯一性
- `standards/archetype-profiles.yaml:428` - drift-check 是定时任务
- `standards/archetype-profiles.yaml:437-439` - owner.holdings: [vcs_admin, intent.ratify, ...]

**问题描述：**
owner 的 vcs_admin 凭据被泄露，攻击者可以修改 ruleset、secret、CODEOWNERS。drift-check §9 对账 admin 唯一性，但这是定时任务，非实时。owner 是唯一信任根，凭据泄露意味着攻击者可执行所有 owner 动作。

**影响：**
- 无凭据轮换流程声明
- 无泄露后的紧急响应流程
- drift-check 是定时任务，非实时检测
- 攻击者使用 owner 凭据走正常路径时，多数检测不触发
- 无多因素认证或操作审计的独立声明

### 4.10 prompt_ref 文件丢失

**问题位置：**
- `standards/context-assembly.yaml:31` - identity: 原型身份提示词
- `standards/context-assembly.yaml:45-46` - fail_closed: 未列入装配清单的内容不得注入
- `scripts/validate.py:284` - prompt_ref 文件存在性校验

**问题描述：**
registry/identities/ 目录被删除，所有 agent 无法加载身份提示词。context-assembly 的 identity 组件依赖 prompt_ref 解析。fail_closed 规则阻止未声明内容注入。identity 无法装配 = spawn manifest 失败 = agent 无法启动。

**影响：**
- 所有 9 个 LLM agent 声明均引用 identities/ 下的文件
- 机制原型无 prompt_ref，可继续工作
- fail_closed 确保不会以"无身份"状态启动 agent，但也意味着无法降级运行
- 无 identity prompt 的备份或版本化恢复机制
- 无"临时 identity"或"最小 identity"的降级路径

---

## 五、系统性问题模式

### 5.1 概念性机制悬空引用

以下机制被引用但未定义/实装：
- `token-path-scope` - 被 archetype-profiles.yaml:61 引用，但无独立实装
- `token-collection-scope` - 被 archetype-profiles.yaml:240 引用，但无独立实装
- `check:pr-identity-path-matrix` - status: planned，未实装

### 5.2 声明与实装脱节

以下声明是纯声明性的，无代码强制：
- `degraded_mode` - 有声明无执行体
- `forward_fix: owner_required` - 策略声明，无 check:* 防线
- `CODEOWNERS` - 依赖 GitHub 平台侧 ruleset 配置
- `write_exclusion` - enforced_by: runtime 但无运行时实现

### 5.3 工具级拦截 vs 路径级拦截

permissions.overrides 按工具拦截，存在间隙：
- builder 的 write_file 被拦截，但 bash 工具不在拦截范围内
- curator 的 write_file 无路径限制，可写 standards/
- adversary 的 datastore_write 是通用的，收窄依赖未实装的 token-collection-scope

### 5.4 声明层检查 vs 运行时检查

validate.py 只在组建/提交时检查，运行时行为不被验证：
- 族独立性检查只在团队组建时运行
- 运行时实际模型族不被校验
- 凭据泄露后的操作不经过族独立性检查

### 5.5 manual_only 控制测试

以下 CT 标注 manual_only，自动化管线不验证：
- CT-CUR-002 - 治理之治理路径 owner-only
- CT-ADV-002 - adversary 只写 findings/**
- CT-RES-003 - 输出封板不可二次加工
- CT-JDG-003 - 管辖域枚举仅 owner 可改
- CT-JDG-004 - 判例非规范
- CT-DEP-002 - 无回滚预案不执行
- CT-DEP-003 - 生产凭据经 environment 审批

### 5.6 escalation 到 owner 后响应路径未闭环

多个场景的共同问题：
- intent_ratification 无超时降级
- 波次冻结后解冻完全依赖 owner
- judge 判决被推翻后无强制要求给出替代方案
- budget 熔断后预算追加路径未声明
- incident_cell TTL 到期后 escalate 动作未定义

体系假设 owner 会及时响应 escalation，但未声明 owner 不响应时的降级策略。

### 5.7 单点故障无分担机制

以下组件是单点且无分担机制：
- LLM Gateway - 所有 LLM 原型停摆
- 数据层 - 所有跨生命周期协作断裂
- interface-gateway - owner 意图无法入境
- scheduler 状态机 - 工作分派停摆
- verifier 机制 - 合并闸门冻结
- curator（单座） - handoff 消费瓶颈
- owner 凭据 - 信任根被攻破
- registry/identities/ - 所有 LLM agent 无法启动
- openJiuwen-ai/jiuwenswarm - 编排框架 upstream 被投毒

### 5.8 fail-closed 设计牺牲可用性

当关键组件丢失时，系统选择冻结而非降级：
- identity 无法装配 = agent 无法启动（无降级路径）
- verifier 持续 fail = 管线完全冻结（无旁路）
- budget 耗尽 = 队永远冻结（无恢复路径）

这在正常场景下是正确的，但在灾难场景下缺乏"安全降级"路径。

---

## 六、问题统计

| 类别 | 问题数 | 严重度 |
|------|--------|--------|
| 流程断点与死锁 | 4 | 高 |
| 角色无法触发 | 5 | 中-高 |
| 反馈死循环 | 8 | 中-高 |
| 基础设施故障 | 10 | 高 |
| 系统性问题模式 | 8 | 中 |

**总计：30 个极端场景，发现 35+ 个具体问题**

---

## 七、结论

本治理体系在声明层面设计严谨，但在实装层面存在多处脱节。主要问题集中在：

1. **owner 是终极单点且无分担机制** - 多个流程断点最终都指向 owner 不可用时的全局停滞
2. **声明与实装脱节** - 多个关键防线是纯声明性的，无代码强制
3. **escalation 到 owner 后响应路径未闭环** - 体系假设 owner 会及时响应，但未声明降级策略
4. **单点故障无备份** - 多个关键组件是单点且无分担机制
5. **fail-closed 设计牺牲可用性** - 灾难场景下缺乏安全降级路径

这些问题在正常开发流程中可能不会暴露，但在极端情况（owner 不可用、基础设施故障、多波次并发）下会导致系统停滞或死锁。
