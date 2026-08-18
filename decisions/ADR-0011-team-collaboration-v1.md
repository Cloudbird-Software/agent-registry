# ADR-0011: 团队协作标准 v1.0——可执行声明与流程彩排门禁

- status: accepted
- date: 2026-08-18
- deciders: owner + AI

## 背景

ADR-0010 建立了九原型+六机制与验证链，但"多 agent 如何组队协作"仍是散点：
协作范式/通信/team 生命周期分布在不同文件且无统一状态机；治理产出（findings/ADR/retro）写完存
着、无强制消费点；owner 注意力阻塞点无预算。v0.1→v0.2 两轮外部评审后形成 v1.0 草案，随后用
双子代理独立复跑（运行时走查 + 对抗审计）暴露了 30+ 条缺陷——其中 9 条 P0（流程走不通级）。
本 ADR 记录定稿决策与缺陷修复。

## 决策

1. **team-collaboration.yaml v1.0（五部分）**：骨架对齐 openjiuwen 不变——协作三范式
   （subordinate/agent_as_tool/handoff）保留原名原义，扩展第四范式 artifact_mediated
   （唯一支持参与方不同时存在的范式——ephemeral 队销毁后产出仍被 stewardship 消费）；
   通信两模式保留，加强制信封。组织：PART 1 协作 × PART 2 团队（scopes/seats/services/teams）
   × PART 3 流与制品（flow 状态机 / artifacts / interfaces）× PART 4 约束 × PART 5 生效（activation）。
2. **声明即执行规范**：simulate-wave.py 消费相位图/权限/预算/账本做确定性流程彩排，
   12 场景全通是 CI required 门禁（validate.yml 双侧运行：base 标准审 head 数据 + head 自洽）。
   任何 AI 复跑结果一致——走查协议编码为回归场景，而非一次性评审。
3. **attention-ledger.yaml**：owner 注意力账本（synchronous≤2 硬断言；asynchronous 全默认动作；
   sampled/auto 显式分类）。conservation_rule：新增 owner-blocking 点必须同时移除一个。
4. **P0 修复（双子代理复跑发现，全部采纳）**：
   - 事故授权矩阵对齐 side-effects 词表（failover/scale 入词表为恢复动作；动作枚举 ⊆ responder.allow
     成模拟器断言）；sev2 回滚 ack 降为 60m 窗+条件默认并入账本。
   - planner 写路径扩展 contracts/（跨卡契约 single_writer 原不可写——N>1 波次死锁）。
   - handoff 逐项声明执行者（team_side: git/归档机制/test_author 相位；stewardship_side: curator
     消费归档资产）；新增 handoff 相位（integrate→handoff 边使 release 停滞状态机可见）。
   - "测试写错了"修复路径：amendment.classify 增 test_fix 类（非减弱型 auto；减弱型降级特权变更）。
   - judge 写权矛盾消解：判决=decision_made 自述事件经平台通道（无写凭据，CT-JDG-001 保持为真）；
     case_law 入库执行者=curator；arbiter 换第三族（sovereign-family/judge-deep 别名）并转正 approved；
     validate 增全局族比对（服务型座位逃逸 team 级检查的通道被关闭）。
   - incident_cell 可实例化：responder/deployer 实例 + incident-cell 队实例（approved 绑定）。
   - 冷启动：delivery_squad trigger=intent.received（planner 随队产示例；ratified=开卡前置非组队前置）。
5. **信任地基补齐**：registry/schemas/ 27 个 JSON Schema（io_contract 全实存，validate 强制）；
   四个服务机制（card-gate/release-bot/knowledge-retrieval/drift-check）注册为机制原型
   （词表 fail-closed 全覆盖；release-bot 持 CT-RLB-001"只部署不开启"）；事件生产者表
   （flow.event_producers——相位图引用的一切事件有主）；severity_classified_by 声明（responder 无定级权）。
6. **双源消解**：flows.yaml 事故节引用 team-collaboration（不再复述授权模型）；change-classes
   logic/prod 的 review/merge 语义对齐 verdict_layers/release 路径（release_bot behind flag +
   flag 开启=owner）；retries 统一"按 risk_class（默认 1）"；backlog ACL 唯一真源在 channels.acl。
7. **CI 自指门禁语义细化**（对 ADR-0010 批次4 的边界修正）：base 标准审 head 数据的防线保留给
   纯数据 PR（C2/C3）；C1 型 PR（standards/scripts/CODEOWNERS/.github 变更）规则与数据必须同源
   演进，base 旧规则审 head 新数据在词汇/结构演进上结构性不可行（实测：词表新增被 base 侧拒绝）。
   此类 PR 的防线=CODEOWNERS owner-only 审查 + head 自洽双跑（validate+simulate 均从 head 运行）。
   防削弱保证不变：纯数据 PR 仍受 base 侧完整校验；标准变更本体属 C1 流程（PR+ADR+owner 批）。

## 四轮评审处置（v0.1→v0.2→v1.0 细节见 git 历史）

- round_1 archetype：10 采纳+2 修正（白名单/拆 checker/operator/adversary+control_tests/平台锁）。
- round_2 teams：16 采纳+4 修正 0 拒绝（时序成员位/amendment/holdout/团队拆分/边界公理/接口/注意力预算）。
- round_3 simulation（双子代理并行复跑：运行时走查+对抗审计）：P0×9+P1×20+P2 若干全采纳；
  关键修正：sev2 ack 60m、holdout 首开杠杆去循环依赖（risk_class/change_class）、
  tests/acceptance 与 tests/unit 分流、escape 回路经 backlog（原队已销毁时序成立）、
  模拟器 or True 空转断言修复+A7 实装。
- round_4 修复验证复跑（新 AI 同协议）：确认 9 条 P0 修复真实落地；另发现修复引入回归 3 条 P1
  （planner 退场条件悬空→补 exit_on；review 裁定无发布面→增 review.* 频道；findings schema
  sources 可空→minItems:1）+6 条 P2（ack_sla 双时钟对齐 60m、planner 工作流补 contracts 步骤、
  event_producers 补 pr.merged/wave.frozen/incident.sev_alert、incident-in 枚举去 sev3、
  amendment-request weakening 条件必填、merge_policy 补 dep/schema 第三钥）——全部修复并编码为
  模拟器回归断言（S1/S10/S11 增强）。

## 后果

- 治理声明从"写给人看"变为"可执行规范"：改声明的 PR 若破坏流程可执行性，CI 直接拒绝。
- 每个角色四命题（有用/能启动/能交付/能信任）有机器可复验的载体（validate+simulate 12 场景）。
- 代价：改 team-collaboration 相位图/权限/授权矩阵需同步过 12 场景——这是有意的（流程声明的
  变更成本应与其影响半径成正比）。
- 遗留（下次迭代）：team.schema（L0）需增 destroy_condition 字段与 re-check-sample 枚举值
  （实例侧已按语义对齐，schema 枚举滞后——跨仓 PR）；check:* CI 名的注册表化。
