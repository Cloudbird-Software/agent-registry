# 红队流程演练问题报告 — Cloudbird-Software 治理体系（.github / CI-Workflows / agent-registry / template-service）

> 本报告基于对三个治理仓库（[Cloudbird-Software/.github](https://github.com/Cloudbird-Software/.github)、[Cloudbird-Software/CI-Workflows](https://github.com/Cloudbird-Software/CI-Workflows)、[Cloudbird-Software/agent-registry](https://github.com/Cloudbird-Software/agent-registry)）以及 [Cloudbird-Software/template-service](https://github.com/Cloudbird-Software/template-service) 模板的端到端流程演练。问题按以下维度组织：A. 校验盲区；B. 流程断点；C. 角色无法被触发 / 任务无人认领；D. 反馈死循环；E. 跨仓一致性与信任断点；F. 极端场景下的无定义行为；G. 其他结构性观察。本报告只描述**客观可观察的问题**，不包含解决方案。

## A. 校验盲区（声明层先决的"防线 ≠ 防线"）

### A1. `expected-state.json` 中的 GitHub App 名称与全部 agent 声明不一致
- 期望状态（drift-check 锚点）声明 `github_app.name = "cloudbrid-agent"`（少一个 d）。
- 全部已批准 agent 的 `credential.github_app` 字段声明为 `cloudbird-agent`（多个 d），至少 6 处：backend-dev、reviewer、responder、deployer、curator-main 等。
- 后果：`drift-check.sh` 校验的是 expected-state.json，而 agent 凭据消费的是 agent 声明。两侧的"真源"不同，drift-check 永远不会因为 agent 凭据改名而报漂移；但 agent 真正去取 token 时按 agent 声明的名字匹配（参见 `gh-app-token.sh`），两套命名之间存在隐性漂移。
- 来源：[`expected-state.json#L38`](https://github.com/Cloudbird-Software/.github/blob/main/governance/expected-state.json#L38) vs 6 个 agent yaml。

### A2. `drift-check.sh` 实际覆盖范围与 `GOVERNANCE.yaml` 声明的 verify 字段严重不对称
- `GOVERNANCE.yaml` 声明了 28 条以上的治理措施，verify 字段分布：
  - `BP-1` `BP-3` `BP-4` `CI-2` `AG-1` `GM-1` `GM-2`（部分）`GM-4`：由 drift-check 覆盖；
  - `BP-2` `AG-3`：声明 `verify: negative-test frequency: weekly, see: T-11`，但仓库内无 T-11 编号、drift-check.sh 不跑；
  - `BP-5` `AG-4` `CI-1` `CI-3` `CI-4` `SC-1` `SC-3` `SC-4` `RL-1` `GM-3` `CG-1` `CG-2` `CG-3` `AR-1` `AR-2` `AR-3` `AR-4` `AR-5` `AR-6` `AR-7` `AR-8` `AR-9`：**全部无 verify 实现**（脚本无对应章节）。
- drift-check.sh 文件结尾（实测读至 80+ 行）只覆盖 §1-§3，**没有 §5-§10**。
  - `GM-2` 声称 `drift-check §8 每日对账直推 commit`，但脚本里没有 §8 章节；
  - `adr-required` 声称 `drift-check §10 每日后验 ADR 存在性`，但脚本里没有 §10 章节；
  - `AR-1` 声称 `registry-validate on: PR` 兜底，但 .github 仓 CI 不跑 validate.py（validate.py 在 agent-registry 仓）。
- 后果：GOVERNANCE.yaml 的 verify 字段构成"声明了但未实装"的大量噪声；CR-B/AG-3/AG-4/SC-* 等关键安全措施无任何运行时对账。

### A3. `validate.py` 中 `deploy/llm-gateway/config.yaml` 对齐检查是 no-op
- validate.py 第 145-150 行：`if GW_CFG.exists(): ...` —— 该文件不在 agent-registry 仓内（`deployment_ref` 指向自身 `deploy/llm-gateway`，但实际无此目录）。
- 后果：models.yaml 与 gateway 配置的别名一致性（ADR-0002 rev1）在仓库内永远不会被校验；只有部署到运行环境后才有意义，但该约束应该 fail-closed 才对。

### A4. `control-tests.yaml` 中 12 条 CT 标 `runtime: manual_only` 无对应运行机制
- CT-TA-004、CT-JDG-003、CT-JDG-004、CT-CUR-001、CT-CUR-002、CT-ADV-001、CT-ADV-002、CT-RES-001、CT-RES-003、CT-DEP-002、CT-DEP-003、CT-RSP-002 全部 `runtime: manual_only`。
- 它们的 `runtime_note` 多为"运行时验证"或"ruleset 防线"或"红队复核"，**但没有任何自动化调度把 manual_only 转为 automatic**：
  - `schedule: weekly`（文件末尾）只针对 `adversary-executed` 类型的 CT；
  - 没有 `manual_only` 调度器；
  - `owner_review: 报告并入 owner 周审` 是文字契约，没有触发器。
- 后果：12 条结构性约束中 11 条从未被持续验证；CT-CUR-002（"治理之治理路径 owner-only"）是单点最危险的一条（P0 标识），但 `runtime: manual_only` + 无调度 = 防线形同虚设。

### A5. `judge` 服务 `agent_tools: max: 0` 与 `researcher` "反向也禁"语义在 validate 缺交叉检查
- `judge` profile 与 `researcher` profile 都声明 `agent_tools: {allow: [], max: 0}`。
- validate.py 只在 `agent → tools` 方向上做 `allow ⊆ profile.agent_tools.allow` 与 `len <= p_max` 校验。
- 缺少的反向检查：`profile.agent_tools.allow` 是否会被某个 LLM 原型声明为 `agent_tools.refs`（即是否真有此原型的 agent 被声明为工具）。若 `profile.researcher` 永远没有 `agent_tools.refs` 引用，max=0 是无意义的常量。
- 后果：profile 词表内的"白名单"为占位符（无任何实际绑定），结构性约束虽然存在但无消费方。

### A6. `attention-ledger.yaml` 的 conservation_rule 缺少"动态守恒"检查
- validate.py 检查 `len(synchronous) <= max_synchronous_per_week`（静态上限）。
- 声明文件本身说"新增 owner-blocking 点必须同时移除一个（账本为证，非口号）"，但 validate 没有"diff 检测"——一次 PR 增加了 2 个 synchronous 项而没移除任何项，依然能通过校验（直到总条数超 max）。
- 后果：conservation_rule 在机制层只表达为"上限"，不能阻止"先加 N 后再减 N"的循环绕过。

## B. 流程断点（状态机/相位图的可执行性）

### B1. `judge` 服务激活计数器无可观察实现
- `team-collaboration.yaml#L137-139`：`judge` 服务的 `activation_counter: metrics-aggregator 计数 verdict_stalemate 事件（scheduler 产）`。
- `verdict_stalemate` 事件的生产者：`mechanism:scheduler`（同文件 `#L271`），但如何判断"同一 PR 的 gate 与 review 结论相反"是机制层的逻辑，无 schema 定义。
- metrics-aggregator 是服务（profiles/archetype-profiles.yaml）有原型，但 `verdict_stalemate_count` 字段从未出现在任何 schema 中。
- 后果：judge 激活条件（"僵持累计 >= 2"）是循环依赖——judge 自身判出的 verdict 算不算？metrics-aggregator 计数的字段在哪？没有 schema 化的 metric，activation 不可复算。

### B2. `red_cell` "连续 3 次调用零有效 findings" 计数器无具体实现
- `team-collaboration.yaml#L150-152`：`pause_trigger: 连续 3 次调用零有效 findings → 暂停两周转纯 owner-invoked`。
- `red_cell` 服务的 `findings_per_week: <=3` 配额与 pause_trigger 共用一套计数。
- 同上：metrics-aggregator 实现的 metric schema 缺失；adversary 的 `output: schemas/findings.json` 也无 `valid`/`nullified` 字段。
- 后果：绝对信号（"零样本即触发"）是 metrics 段写的"无须 min_sample"模式，但触发所需的事件源/字段都没有 schema 化定义。

### B3. `release_record.rollback_safe` 的判定逻辑不在声明层
- `team-collaboration.yaml#L338-340`：`release_bot 于每次部署 behind flag 时写入 release_record` `rollback_safe=false 当且仅当发布含 contract 相迁移/不可逆副作用`。
- 没有任何"什么算 contract 相迁移"的判定规则、阈值、或白名单；
- release_bot profile（archetype-profiles.yaml）只声明"部署必写 release_record"；
- `verifier` 的 `evidence_policy.tier_order` 是验证证据层级，与 rollback_safe 无关。
- 后果：rollback_safe 字段由人/agent 主观填写；incident_cell 的 sev1 预授权矩阵（"preauthorized_if: release_record.rollback_safe AND within rollback_window"）依赖这个主观字段。

### B4. `card.test_tree_sha` 的"测试树冻结"无冻结来源
- 多个 agent/team 声明（planner、test-author、builder）都引用 `test_tree_sha`，但这个 sha 的产生者在声明层缺失：
  - test-author profile：`实现开始前把规格转译为测试并冻结（test_tree_sha 回写卡）`；
  - 但 test-author 的 io_contract.output 是 `schemas/test-suite-out.json`，无 `test_tree_sha` 字段要求；
  - registry 提供的 schema 列表中无 `test-suite-out.json` 的字段定义可见（仅在路径上引用）。
- 后果：`test_tree_sha` 字段存在于 card 字段表（team-collaboration artifacts.card），但如何产生、谁产生、产出 schema 是什么——声明层断链。

### B5. `incident_cell` 的 `deployer` 座位在 team YAML 中"常备绑定"与 agent role 中"仅 sev1 前进修复"矛盾
- `incident-cell.yaml`：`members: deployer count: 1 as_tool: false`（常备绑定）；
- `deployer.yaml` role：`仅 incident_cell 场景：sev1 且回滚不可行的前进修复，owner_required`；
- `team-collaboration.yaml#incident_cell.seats.deployer: "0..1"`（按需）。
- 三处声明的"deployer 是否常备"答案不同（常备 / 0..1 按需 / 仅 sev1 前进修复），且无声明层指明何者为准。
- 后果：实际投产时，incident_cell 实例化是否会预占 deployer 座位不可判定；常备绑定可能造成 deployer 在不需要前进修复的事故中也消耗预算/注意力。

### B6. `severity_classified_by` 双源（外部告警标签 vs owner 指定）皆无的具体映射
- `team-collaboration.yaml#L213`：`告警源标签或 owner 指定；皆无 → sev2（保守默认——不误开 sev1 预授权；responder 无定级权）`。
- 外部告警的"标签→severity 映射"无任何表/规则/声明；
- sev1/sev2 预授权矩阵不同（deploy_reverse 在 sev1 有条件预授权，sev2 则 ack 60m 窗内由 owner 决定），如果告警源默认到 sev2 而实际损失面是 sev1，response 速度会受影响。
- 后果：默认 sev2 保守但可能造成 sev1 漏判（owner 60m 内未必查 ack），延长 MTTR。

### B7. `escape_found` 事件有生产者（owner）但 owner 受理流程未声明
- `team-collaboration.yaml#L272`：`escape_found: owner（经 interface-gateway/周审受理，平台落事件）`。
- 受理流程（"周审受理"）无固定周期、无 SLA、与 attention-ledger 的 weekly_review 是同一物还是不同物无说明。
- 后果：escape 信号从生产到处置之间存在不可观测的"人工时延"（周审 = 0~7 天），与 24h retro 债（CT-RSP-002）的不对称节奏相互干扰。

## C. 角色无法被触发 / 任务无人认领

### C1. `incident_cell.deployer` 的激活条件覆盖缺失
- sev1 前进修复要求"owner_required"（incident_cell.authorization.sev1.forward_fix）；
- 但 deployer 激活需要（a）sev1 告警（b）回滚不可行（c）owner 在场。
- 三个条件交集由谁判定？responder 报告"回滚不可行"？但 responder 的 allow 不含 schema_migrate（部署工作归 deployer），所以它无法自证"回滚不可行"。
- 后果：deployer 的触发链在 (b) 步就断链——既无机制判定"rollback infeasible"，又无 owner 提前授权模板。

### C2. `red_cell` 配额与触发时序无状态机
- `findings_per_week: "<=3"` + `forced_ranking_top: 5` + `archive: 全量归档可查` —— 但每周调度的发起者、调度时间窗、与维护回路（maintain_loop）的关系不明确。
- 触发条款 `on: [重大决策前 premortem, 控制测试排期, gaming 信号, owner 随机抽发]` 中"重大决策前"的判定没有定义（什么算"重大"？C1 治理资产变更？schema 迁移？）。
- 后果：red_cell 可能因配额耗尽而错过"重大决策前"的 premortem；或"随机抽发"从未发生（owner 不会主动）。

### C3. `judge` 服务的"无自批"边界依赖外部判定
- `judge` profile `isolation: hermetic`、`agent_tools.max: 0`、`allow: [fs_read, vcs_read, datastore_read]`。
- 但调度时谁决定"分歧是否可机械判定"？team-collaboration.yaml `#L285`：`'测试写错了'先走 test-author 修复路径（amendment.test_fix）；僵持才仲裁`。
- 僵持的判定需要"双方主张已结构化提交"（同文件 #L271 verdict_stalemate 判定），但 amendment_request 提交后是否"已结构化"是 judge 的事；无前置于 judge 的预筛机制（证据 evidence-pack 包含 flaky 预筛但只在 judge 内部步骤中）。
- 后果：第一个僵持必然"卡在判定是否僵持"的循环——judge 未激活前僵持直达 owner，owner 怎么处理"是否僵持"无标准模板。

### C4. `interface_gateway` 自身的"分类器"声明但无实现
- `intent-routing.yaml#L94-97`：`classifier: interface-gateway（机制）：intent.received 事件落库后按本表 what/examples 语义匹配 + 变更面探测（diff 面积/路径/依赖）自动归类`。
- interface-gateway 的 profile（archetype-profiles.yaml）只声明 `nl-to-intent` 薄 LLM 层。
- 语义匹配 + diff 面积探测的算法未声明；"歧义时按更重一侧路由并向 owner 确认一次"也未声明"确认"通过什么渠道（TUI 弹窗？邮件？）以及"更重一侧"在七分类中的相对权重。
- 后果：fix vs deliver 的歧义路由无法用代码判定，必然走 owner 兜底，与 attention-ledger 守恒冲突。

### C5. `curator` 的"backlog 单写者" vs `adversary` 不直写提案的约束传递链无校验
- 全部声明均约束 adversary 不直写 backlog.proposals，但 validate.py 没有任何"按 team 写权限反查"的检查——adversary agent 自身的 `allow: [...]` 确实不含 backlog 写权限，所以 validate 不会报；但 channel 层 ACL（pub_sub.backlog.proposals.*）的 `write: [curator, responder, owner, planner]` 在声明文件中存在，没有任何脚本消费它——"声明写了 ≠ 平台执行了"。
- 后果：channel ACL 是文字契约；如果平台实现忽略此 ACL，adversary 仍可经合法 channel 写 backlog（看渠道层是否真在强制）。

## D. 反馈死循环与无定义行为

### D1. `intent-routing.fix` 的"升级例外"判定无终止条件
- `change-classes.yaml#L21-25`：trivial.promote_if 含 4 条升重条件。
- 升级后的卡（logic/dep/schema）走回 deliver 流，进入 intent_ratification；
- 但回不到 trivial 的判定没有声明——一旦 promote，回不去了（intent-routing demotion 段："升重不可逆（trivial→logic 后不因'改完了'降回）"）。
- 后果：trivial 卡的 promote 决策是单向门；触及 `tests/acceptance/**` 的卡立即升 logic，可能把"小修"逼成"必须 owner 批示例"的 deliver。

### D2. `amendment` 的 escalate_when（"同卡 >= 2 → 回炉；同波次 > 3 → 冻结新开卡"）无计数实现
- `team-collaboration.yaml#L322`：`escalate_when: 同一卡 normative amendment >= 2 ... 同波次 > 3 → 冻结新开卡+escalate owner`。
- card_gate 计数声明存在（"executor: card_gate 计数与分类"），但 card_gate 的实现声明（archetype-profiles.yaml `card-gate`）只说"schema/capability_tags/DAG/testability_signoff/knowledge 处置/contracts/test_tree_sha 逐项机械检查"，**无计数器声明**。
- 后果：escalation 触发所依赖的"连续 N 次"在声明层无字段、无事件、无 schema。

### D3. `card.aborted` reason_routing 三路善后的实际执行者缺失
- `flows.yaml#L106-110`：`need_gone: 卡 archived(作废)；spec_wrong: 产 escape 类 finding 退 backlog；superseded: 关联新卡 id 落事件`。
- "关联新卡 id 落事件"：原卡 archived 后关联新卡的关系如何表示？card schema 中无 `supersedes_id` / `superseded_by_id` 字段；
- "spec_wrong → 产 escape 类 finding"：escape_review 在 flows.yaml 中是 owner 手工触发的闭环（step 1-4），abort 的自动转 escape 路径与 owner 手工触发是同一接口还是独立通道无说明。
- 后果：abort 的善后是"reason 决定"但善后动作是"卡 archived"——若实际机制只做 archived，三路善后都退化为同一终态。

### D4. `incident_cell.authorization` 的 owner_ack_within(60m) 超时语义
- `team-collaboration.yaml#L227`：`deploy_reverse: "owner_ack_within(60m) else (rollback_safe ? deploy_reverse 预授权 : data_freeze)"`。
- 60m 内未 ack → rollback_safe ? deploy_reverse : data_freeze。
- "owner 未 ack" 与 "owner 明确拒绝" 是不同状态；声明把两者合并为同一超时路径。
- 后果：owner 主动看了但还没回复（"研究一下"），系统已经在等 60m 之后部署反向；owner 误以为还在自己掌控下。

### D5. `planner.state == exited` 的退出条件与重入语义不对称
- `team-collaboration.yaml#L97`：`planner: present_in_phases: [plan] exit_on: cards.ratified reentry: on_normative_amendment state_on_reentry: active`。
- "exit_on: cards.ratified" —— 一旦 card_gate 输出 ratified，planner 退出；
- "reentry: on_normative_amendment" —— 发生规范性 amendment 时 planner 重入 active；
- 但 builder 还在 build 期间（card.ratified 之后），planner 已退出；若此时发生 normative amendment，planner 重新 active，但 builder 还在原卡上工作—— write_exclusion 不变式（"planner 重入期间 builder 必须 frozen"）的触发需要"planner.active AND builder.active AND 同一 artifact" 的检测，无机制实现。
- 后果：planner 重入与 builder 冻结的同步是逻辑正确但运行时无保证。

### D6. `curator` 提案审核（10% 抽检）的"否决"路径无事件
- `attention-ledger.yaml#sampled.non_normative_amendment_veto: rate: 10%, apply: auto + owner 抽检否决`。
- "抽检否决" 后 amendment 怎么回滚？非 normative amendment 已经 auto apply 了；需要回滚产生新 commit？还是撤回原 PR？
- 后果：抽检的语义是"抽中后才审"，但否决的"善后路径"无事件、无 schema。

## E. 跨仓一致性与信任断点

### E1. `.github` 仓的 CI 不跑 `validate.py`
- `AGENTS.md`（agent-registry）："团队协作声明是可执行的：`scripts/simulate-wave.py` 是 CI required 门禁"。
- 但 `.github/standards/team-collaboration.yaml` 的修改（如果由 .github 仓做出）的 CI 校验是什么？`.github/workflows/` 没有 `validate.py` 引用。
- `checks.yaml` 中 `adr-required` 声明：`agent-registry validate.yml + .github gate.yml + CI-Workflows ci.yml 的 adr-required 步骤`——但 .github 仓的 `gate.yml` 在克隆中未找到（drift-check.sh 引用的 gov 路径是 `.github/governance/`）。
- 后果：.github 仓的 `standards/` 变更只能依赖 agent-registry CI 跑（如果设置 cross-repo 触发），否则无校验。

### E2. `CI-Workflows` 仓本身缺 CODEOWNERS 与 adr-required
- `CI-Workflows/.github/` 仅有 workflows/ 和 dependabot.yml；无 CODEOWNERS、无 governance/、无 adr-required gate。
- `apply.sh` 不覆盖 `CI-Workflows` 仓库基线（apply §5 全分页拉取所有 org 仓并设 squash-only+delete_branch_on_merge；OK）。
- 但 CI-Workflows 仓的"治理之治理"路径无 owner-only review gate——任意 maintainer 可合并工作流修改。
- 后果：CI-Workflows 仓若被攻破，drift-check 拉取的 expected-state.json / apply.sh 仍信任它（drift-check 不验证脚本本身的真源）。

### E3. `drift-check.sh` 中 `expected-state.json` 自身无对应 ADR
- `GOVERNANCE.yaml` 声明 governance_change 流程 C1 变更须附 ADR。
- `expected-state.json` 内容（含 `actions_policy`、`code_security`、`repo_baseline`、`github_app` 等关键安全字段）的修改是否属于 C1 范围？`flows.governance_change.classes.C1.scope` 列出 `governance/` 整目录——包含 expected-state.json。
- 但 expected-state.json 内容的"漂移修复"（drift-check 报漂移后人工改文件）走什么流程？`apply.sh` 写回的是 API 状态，不是 expected-state.json 本身。
- 后果：expected-state.json 与 apply.sh 之间的"以哪个为真"在 C1 流程下是双真源（apply 写 API 不会回写 expected-state.json；改 expected-state.json 不会自动调 apply.sh）。

### E4. `template-service` 的 ci.yml 不调 hygiene / 不调 zizmor
- `template-service/.github/workflows/ci.yml`：调 `CI-Workflows/.github/workflows/check.yml@v1`（make setup + make check）与 `dep-review.yml@v1`，但**不调 `hygiene.yml`**（gitleaks + secret-ish + 大文件检查）。
- `CI-Workflows/.github/workflows/hygiene.yml` 存在且 `workflow_call` 模式可被消费，但 template-service 的 ci.yml 未引用。
- 后果：template-service 派生出的新仓将无 secret scan 防线（除非新仓自己加），与 CI-1 "每 PR: lint+arch+test+hygiene+dep-review 聚合为 gate" 声明不符。

### E5. 跨仓 refs（如 `uses: Cloudbird-Software/CI-Workflows/.github/workflows/check.yml@v1`）的版本钉死不一致
- template-service ci.yml：`@v1`（浮动 tag）；
- `adr-required` check 声明："引用 `@v1`"——同一形式；
- zizmor.yml 注释提到"ADR-0011 遗留项落地：scorecard PinnedDependencies"。
- 但 `@v1` 是浮动 tag，CI 在重拉时会拿到新 v1.0.x 修订。scorecard 的"下载钉死"建议与生产实践在"仓级 reusable workflow"维度上冲突。
- 后果：可复用工作流的"修订"可能不可观察地引入新 gate 行为；测试场景（scenarios）可能因 CI 端默默变更而发生不可复现的失败。

### E6. agent-registry 的 `deploy/llm-gateway` 目录缺失
- `models.yaml` `gateway.deployment_ref: "Cloudbird-Software/agent-registry deploy/llm-gateway"`。
- 实际 git tree 中无 `deploy/llm-gateway/` 目录。
- ADR-0002 rev1 声称 gateway 配置与 models.yaml 别名一致，validate.py 第 145-150 行检查该文件但 `if GW_CFG.exists()` 静默跳过。
- 后果：别名一致性约束无落盘；运行时配置错配时 validate.py 不会拒。

## F. 极端场景下的无定义行为

### F1. owner 长期缺席时的注意力兜底
- `intent_ratification` 是 synchronous 项，无 default；
- sev1_forward_fix_authorization 也是 synchronous 项，无 default；
- 两者在 owner 缺席时无 fallback。
- attention-ledger.conservation_rule 静态检查不强制守恒；长期 owner 缺席时不会自动降级。
- 后果：owner 不可用时，整个系统进入"等 owner"状态（无 degraded mode 自动接管）。

### F2. LLM Gateway 全节点不可达
- `models.yaml` `gateway.strategies: [failover, quota-routing]`，无降级策略；
- team-collaboration.yaml `activation.on_trigger.degraded_mode: {when: "可用族数 < 激活中的独立性需求（family_priority 动态排：judge>test_author>builder，未激活的不占族）"}`。
- "可用族数 < 激活中的独立性需求" 是触发条件，但触发后做什么（降为同族？暂停卡？abort？）无默认动作。
- 后果：degraded_mode 触发后系统进入无定义状态——声明"按 family_priority 排"但排完怎么裁决无。

### F3. judge 服务被同时召唤多次（多个 PR 同时僵持）
- `judge: per_dispute 一次仲裁一实例，判后销毁`；
- "per_dispute" 的定义是"一次争议"还是"一个 PR"？若 N 个 PR 同时僵持，N 个 judge 实例需 N 不同的族——sovereign-family 的 `route_group: sovereign-pool` 是否能多实例？
- `independence: 同一 dispute 不得复用上次实例` —— 但"上次实例"无生命周期记录。
- 后果：并发召唤可能造成实例复用违反独立性（如果 sovereign-pool 容量 < N），或路由不到（如果无多余节点）。

### F4. ephemeral 队销毁失败时 memory_digest 的兜底
- `team-collaboration.yaml#lifecycle.destroy: "after-handoff(team_side) AND (released_behind_flag OR reverted)"`；
- handoff 中 `memory-export: seat:planner + seat:test_author`；
- 若 handoff 某步失败（机制层无 retry 说明），destroy 条件未满足 → 队不销毁。
- 但 seat 的"已写过 memory_digest 但未消费"是中间态——curator 何时消费？`stewardship_side: [memory-distill, adr-write]` 是异步消费。
- 后果：若队因 destroy 条件未满足而长期保留，memory_digest 不会被 steward 看到（stewardship 消费的是"已销毁"的归档）；若强行销毁则"先于 workspace 销毁过界"被破坏。

### F5. `card.paused` 状态下卡被 amendments 同时提交
- `card.paused` 的 target_states 是 `[building, verify]`，owner_control 语义"停表停预算"；
- amendment_request 仍可能到达（builder↔test_author 之间的 amendment）；
- 暂停态下的 amendment 是 apply 还是 hold？声明无。
- 后果：暂停期间若有 test_weakening 类 amendment 到达并 auto apply（test_fix 类的非减弱型），paused 卡可能在 owner 不知情下被修改。

### F6. 跨仓 ADR 引用不可达
- `checks.yaml#adr-required`：`PR title/body 无 ADR-NNNN 引用、或被引 ADR 不在 PR head 的 decisions/ 则 fail`。
- 但 .github 仓本身的治理变更引用的 ADR 在 agent-registry/decisions/（PR 上下文 GITHUB_TOKEN 无跨仓读权，CI-Workflows ci.yml 注释说明）。
- 后果：跨仓 ADR 引用的合法性检查只能由 `.github drift-check.sh §10 每日后验`（`adr-required` 声明），但该 §10 不存在（A2 已述）；前端 fail-closed 看不到 ADR 文件导致"误报 fail"。

### F7. `check:precedent-non-normative` 状态为 `planned`，但 `precedent-non-normative` 是 check 还是规范？
- `checks.yaml#L67-69`：`status: planned, where: case_law 入库时非规范标注（curator）——随 case_law 激活（on_trigger：judge 争议累计 >= 5）`。
- `judge` profile 中 `CT-JDG-004` 也是 `runtime: manual_only` + `runtime_note: case_law 未激活（on_trigger）`。
- case_law 激活条件是 `judge 争议累计 >= 5`，judge 激活条件是 `僵持累计 >= 2`——后者未达前者不可能激活，但 `judge 争议` 的累计度量无 schema（B1 已述）。
- 后果：case_law 与 precedent-non-normative 形成"前置条件依赖不存在的计数器"的双重未激活。

### F8. `intent-routing.intents.ask` 的 evidence_based 验收无证据门槛
- `ask` 意图 `acceptance_source: evidence_based`；
- intent-routing 段无 `evidence_based` 验收的具体门槛（什么算"被证据回答"）；
- `flows.yaml#L25-27`：`investigate/spike: 问题被证据回答即合格；guard: 结论必须附引用（禁无证据断言——findings.json sources minItems:1）`。
- 但 ask 的输出 schema 是 `query-in.json` → 输出（agent 自身回答），与 findings.json 不是同一 schema。
- 后果：ask 意图返回无引用回答在声明层无禁止（只有 ask_retrieval.contract 文字约束"查不到就说查不到"）。

### F9. 治理仓自身的 "C1 必附 ADR" 与 governance drift-fix 的因果环
- `GM-2`：`破玻璃=直推后 24h 内回填`；
- `drift-check §8`：策略生效日之后默认分支的非 PR commit = 漂移（声明，但 §8 不存在）。
- 真正的破玻璃回填（apply.sh 修复 expected-state.json 与线上不一致）有时本身就是非 PR 直推（owner 紧急回滚）。
- 后果：owner 紧急回滚触发 §8 漂移 → 触发回填 PR → 24h 截止前必产 ADR；但紧急回滚往往来不及写 ADR，循环。

## G. 其他结构性观察

### G1. `team-collaboration.yaml` 与 `intents.*` 的 `carrier` 引用正反方向不对称
- validate.py 检查"intent:carrier 引用不存在的团队原型"（正向），但反向不查"团队原型被哪个 intent 引用"——可能存在无 intent 引用的死团队原型（当前有 delivery_squad / stewardship / incident_cell 三个全部被引用，OK；但新增原型时不会校验）。

### G2. `simulate-wave.py` 仅有声明式 assert + 12 个 hook 混合
- S1-S12 用 hook（Python 函数）；
- S13-S20 用声明式 assert；
- hooks 的覆盖率在 scenario 文件中只通过"hook: scenario_xxx"字符串引用，无路径/存在性校验。
- 后果：scenario 注册表与 hook 实现脱钩——hook 函数改名/删除 scenario 注册表察觉不到。

### G3. `owner` 伪原型在 agent 校验中是被豁免的（OK），但其引用也无验证
- 团队声明中 `external_audit.team: null:owner` 是合法值（validate.py 特判 `eat.startswith("null:")` pass）；
- 但 `null:owner` 语义是什么？既不是 principal 引用也不是 team 引用，与 team-collaboration.yaml `principals.owner` 不同源。
- 后果：principal 的"审计方"语义在两处声明有不同含义（owner 周审 vs null:owner 字段）。

### G4. `curator` 跨仓 + ADR 提案的"提案权"无流程对接
- `curator` role：`对 standards/validate 的修改只有提案权`；
- 但 curator 的 io_contract output 是 `schemas/curation-out.json`，无 `proposal` 字段要求；
- 提案如何入 backlog？curator 与 owner 之间是否仅通过 PR（owner 批 C1 路径）？无中间态（草稿评审机制）。
- 后果：curator 的提案在 owner 看到前无法被"对照"。

### G5. `arbiter` 与 `red-adversary` 的模型族 `sovereign-family` 无上游映射
- `models.yaml` 声明 `sovereign-family` 与 `sovereign-pool`；
- `gateway.upstream_runtime.repo: openJiuwen-ai/jiuwenswarm` 声明上游，但 `family` 与上游模型族的对应关系无字段；
- 后果：sovereign-family 实际是"无映射的占位 family"，独立性的真实性（CT-TA-002、CT-JDG-001 的"族映射与上游实际家族一致"运行时验证）无锚点。

---

## 受影响的核心声明文件清单

- [`standards/team-collaboration.yaml`](https://github.com/Cloudbird-Software/agent-registry/blob/main/standards/team-collaboration.yaml) — B/C/D 主要问题集中处
- [`standards/intent-routing.yaml`](https://github.com/Cloudbird-Software/agent-registry/blob/main/standards/intent-routing.yaml) — C4
- [`standards/change-classes.yaml`](https://github.com/Cloudbird-Software/agent-registry/blob/main/standards/change-classes.yaml) — D1
- [`standards/control-tests.yaml`](https://github.com/Cloudbird-Software/agent-registry/blob/main/standards/control-tests.yaml) — A4
- [`standards/checks.yaml`](https://github.com/Cloudbird-Software/agent-registry/blob/main/standards/checks.yaml) — A4/F6/F7
- [`standards/attention-ledger.yaml`](https://github.com/Cloudbird-Software/agent-registry/blob/main/standards/attention-ledger.yaml) — A6/F1
- [`standards/archetype-profiles.yaml`](https://github.com/Cloudbird-Software/agent-registry/blob/main/standards/archetype-profiles.yaml) — B5/C1/G5
- [`standards/flows.yaml`](https://github.com/Cloudbird-Software/agent-registry/blob/main/standards/flows.yaml) — D3
- [`standards/scenarios.yaml`](https://github.com/Cloudbird-Software/agent-registry/blob/main/standards/scenarios.yaml) — G2
- [`scripts/validate.py`](https://github.com/Cloudbird-Software/agent-registry/blob/main/scripts/validate.py) — A3/A5/A6
- [`registry/models.yaml`](https://github.com/Cloudbird-Software/agent-registry/blob/main/registry/models.yaml) — E6/G5
- [`registry/agents/*.yaml`](https://github.com/Cloudbird-Software/agent-registry/tree/main/registry/agents) — A1
- [`.github/governance/expected-state.json`](https://github.com/Cloudbird-Software/.github/blob/main/governance/expected-state.json) — A1/E3
- [`.github/governance/drift-check.sh`](https://github.com/Cloudbird-Software/.github/blob/main/governance/drift-check.sh) — A2
- [`.github/governance/apply.sh`](https://github.com/Cloudbird-Software/.github/blob/main/governance/apply.sh) — E3
- [`.github/governance/GOVERNANCE.yaml`](https://github.com/Cloudbird-Software/.github/blob/main/governance/GOVERNANCE.yaml) — A2
- [`CI-Workflows/.github/workflows/*`](https://github.com/Cloudbird-Software/CI-Workflows/tree/main/.github/workflows) — E2/E5
- [`template-service/.github/workflows/ci.yml`](https://github.com/Cloudbird-Software/template-service/blob/main/.github/workflows/ci.yml) — E4

---

> 本报告为客观问题清单，**不包含解决方案**。所有引用均经过 .github 仓 governance 与 standards 的对照验证。报告由红队流程演练产出，演练方法：本地克隆三仓 + 运行 validate.py / simulate-wave.py（baseline OK）+ 五维度红队攻击场景（角色触发、校验绕过、跨仓一致性、极端场景、状态机断点）。
