# ADR-0010: Governance v3 —— 威胁模型重排与角色体系重构

- 状态: proposed（随本 PR 批准）
- 日期: 2026-08-18
- 取代: ADR-0008（archetype v2 十原型）与 ADR-0009（profiles v1）的相应结论；ADR-0007 的 AR-9 验证链表述
- 主题: 副作用词表 v2 / 白名单制 / checker 与 operator 双拆分 / LLM-机制二分 / 信任区 / 控制测试 / 闭环两端 / 平台锁

## 背景

外部审计（另一模型）对 archetype v2 体系提出 12 条 P0 级反馈。核心判断成立：**防御预算错配**——v2 花主要力气防"agent 合谋自证"（低频低损），而对一人公司真正致命的三类风险（意图失真、现实逃逸、供应链注入）几乎无防御；且副作用分类过粗导致至少 5 处声明自相矛盾。

经独立评估：12 条 P0 全盘认可 10 条、修正后接受 2 条；威胁模型按以下排序重新分配机制预算：

```
造错东西（意图失真）> 供应链/注入 > 成本跑飞 > 治理过重导致 owner 绕过 > agent 合谋
```

审计中一处事实错误已核实排除：org 为 Team 计划，agent-registry 私有仓的 environment required reviewers **可用且已生效**（production 环境实测带 required_reviewers）；三个 org ruleset 的 bypass_actors 实测为空。但"ruleset 路径规则不区分 actor"的方法论正确——身份×路径矩阵由 token scope + required check 实现，不指望 ruleset 路径规则。

## 决策

### 1. 副作用词表 v2 + 白名单制（消 5 处矛盾，关 fail-open）

- `standards/side-effects.yaml`：六组词表（read/write/vcs/exec/supply/infra，24+1 种）。
- 权限从黑名单（forbidden_*）改为 **capabilities.allow 白名单**：未列出即禁止，加新原型/新副作用时旧声明自动 fail-closed。
- 组合规则（validate 强制）：agent 持有的每个工具，其 side_effects 必须 ⊆ 该 agent 的 allow。
- `fs_write_sandbox`（任务级暂存，随任务销毁）对持有 shell_sandbox 的原型开放；gitcode-pr 的 API 传输读不算 net_read（外部摄取语义只属于 web_search/researcher）。

### 2. checker 双拆分：test-author（LLM 出题）+ verifier（机制判卷）

v1 的元层漏洞：checker 既写测试又用自己的测试判决——放松断言即可自洽，mutation score 杀不死"编码了错误需求的测试"。v2：

- **test-author**：只出题（tests/acceptance/**），实现开始前冻结测试树（test_tree_sha 记录在卡），判卷阶段零介入；减弱型变更（删测试/删断言/放宽/skip）是特权变更（新卡+owner 批+test_weakening 事件）。
- **verifier（机制）**：跑冻结树产 verdict（required status check），无 LLM 主体，evidence_policy 分层（deterministic > property > golden > llm > human；高风险卡禁纯 LLM 判决）。
- 测试分层：unit（builder 设计工具）/ acceptance（判决依据）/ hidden holdout（**二期**：独立仓，失败只回断言 id——anti-overfit 的 Kaggle private leaderboard 逻辑）。
- builder 恢复 unit 测试作者权（v1 全禁是错的——毁 TDD 设计价值）；acceptance 树对 builder 只读。

### 3. operator 双拆分：deployer（前进，逐动作人签）/ responder（恢复，预授权先做后报）

v1 对称人签的逻辑错误：MTTR = owner 的睡眠时间。v2 权限非对称：deployer 无回滚权，responder 只能恢复不能前进（白名单枚举恢复动作，async_notify 全留痕，24h retro 债由 curator 追踪）。

### 4. LLM/机制二分：能确定的用代码

v1 十原型中 4 个本质是确定性控制流，用 LLM 实现徒增不确定性、成本与注入面。v2 分层：

- **LLM 原型（9）**：builder / planner / test-author / judge / curator / adversary / researcher / deployer / responder
- **机制原型（6，无 LLM 主体，至多薄 llm_assist）**：verifier / integrator / scheduler / evidence-pack / interface-gateway / metrics-aggregator
  - scheduler：状态机调度+预算熔断；LLM 仅失败归类（无重试裁量）
  - interface-gateway：网关代码；LLM 仅 NL→intent 解析（薄，须过 schema）
  - metrics-aggregator：代码/SQL 聚合（保证"可复算"承诺为真）；LLM 仅异常叙述
- **伪原型 owner**：信任根显式存在——vcs_admin 唯一持有者、intent 批准、管辖域唯一修改者、一切判决可推翻。
- **合并=状态函数（P0-6）**：vcs_merge 不授予任何 agent，integrator 机制机械触发（checks 全绿+verifier verdict+卡号 metadata）；治理仓 C1/C2 永远 owner 手合。

### 5. 新增 adversary + control_tests：把断言变成被验证的事实

v1 全部 structural 条目是断言。v2：

- 每条 structural 必须 {claim, enforced_by, control_test} 三字段非空（validate 强制）。
- `standards/control-tests.yaml` 登记 28 条 CT；validate 强制 profiles 引用的 CT 全部登记（ct-coverage）。
- **adversary** 原型（实例 red-adversary）按清单以目标原型真实凭据尝试越权，期望失败；期望失败却成功 → P0 事件+冻结。附带 premortem（出失败模式清单，不出判决）。
- 无人可审审计者 → 由制度审：adversary 沙箱一次性、findings 只进数据层、不被任何 agent 调用。

### 6. 信任区与注入防护（P0-8）

- trust_zones：untrusted_ingest（仅 researcher 可 net_read）/ trusted_control；interface 降为机制后不直接触外部文本（NL 解析输入只来自 owner 通道）。
- researcher.agent_tools = 0（双向：它不调 agent，也不被用于给特权节点洗输入）。
- findings 必须 schema 化+provenance+source_class(internal_repo|external_web)；external_web 结论不得作为判决/政策规范依据。
- judge 证据只允许仓内固定 ref 材料 + evidence-pack artifact（平台产的不可变重跑证据）；flaky 类机械预筛（N 次 M 失败自动判，不经 judge）。
- 判例 normative=false；同类争议 ≥3 → policy_gap findings 交 planner 开卡；管辖域枚举 owner-only。
- "外部读取→写类动作"同 run 序列进异常检测。诚实声明：imperative-strip 为 best-effort，能硬保证的只有 schema 隔离+provenance+序列检测。

### 7. 闭环两端（比合谋更重要的两件事）

- **intent_ratification**（flows.yaml）：planner 产 5~15 条验收示例（owner 30 秒可读）→ owner 逐条批（签名+hash 落事件流）→ 未批准不得开卡（scheduler 前置）。人审点从"计划评审"移到"验收标准批准"——意图保真是 owner 注意力的最高杠杆。配套 acceptance digest（一屏证据包，不是只给 verdict:pass）。
- **escape_review**（flows.yaml）：逃逸缺陷强制归因（spec_gap|test_gap|impl_gap|env_gap）→ 必产回归测试 → 按归因更新模板/政策 → escape_rate 周报。这是唯一能真实评价验证体系的指标。
- 计划评审重构（P0-12）：checker/test-author 退出计划评审；结构由代码校验（validate），价值由 owner 批验收示例，风险由 adversary premortem。

### 8. 平台锁（治理之治理）

- **自指门禁修复**：gate 工作流 PR 事件时标准侧（validate.py+profiles+词表+CT）从 base ref checkout，数据侧从 head；REGISTRY_DATA_ROOT 分离两棵树。同 PR 削弱门禁自审的路径关闭。
- **CODEOWNERS**（两仓）：standards/** / scripts/validate.py / CODEOWNERS / .github/** owner-only；ruleset 开 require code-owner review（合并后配置）。
- **vcs_admin 唯一性**：org 全部仓库 admin 数 == 1 且为 owner——归 drift-check §9（API 对账），不归 validate（离线 YAML 校验器查不了平台权限——机制放错层会制造"声称的强制不存在"）。
- **事件完整性**（flows.yaml event_integrity）：emitted_by 强制字段；tool_called 只能 platform（网关带外）；append-only+哈希链；写凭据与所有 agent 隔离。
- **预算熔断**（flows.yaml budget）：per_card {tokens, wall_clock, retries≤1, usd}，gateway 虚拟 key 硬顶，超限 fail-closed 回 planner——重试是机制不是裁量。
- **change_classes**（standards/change-classes.yaml）：doc/logic/dep/schema/prod 五级，仪式感与影响半径成正比（anti-ritual-creep）；expedited 降级必须 3 天内补 retro-ADR（curator 追债）。

### 9. 模型独立性升级为族级

v1 别名级太弱（两个别名可能同族；自偏好偏差在同族同样存在，Panickssery et al. 2024 / Wataoka et al. 2024）。v2：models.yaml 每别名加 family；validate 按族判定 test-author/judge 与争议方不同族。修正 v1 失配：别名隔离确实在 validate 强制（PR #4 已修），但 model_tier 确实未强制而 duty_assurance 措辞过度声明——v2 的 typical 明确标注指导性。

### 10. 对审计意见的三处不采纳（记录在案）

1. "80% 力气防合谋"的度量——定性方向接受（预算重排），量化论据不成立（防合谋项均为一次性低成本声明）。
2. 证据阶梯把 human 放最弱档——范畴错误：owner 批验收示例是目标设定（意图定义阶梯要证什么），不是正确性证据链一环。tier_order 作为正确性证据排序采纳，human 移出序列。
3. 三个机制降级推到底（interface/orchestrator/observer 全无 LLM）——各保留一处薄 llm_assist（NL 解析/失败归类/异常叙述），判断没有消失，只是被限制在无裁量的位置。

## 被推翻的先前决策

| 先前 | 处置 |
|---|---|
| ADR-0008 十原型（checker/operator/orchestrator/interface/observer 为 LLM） | checker→test-author+verifier；operator→deployer+responder；orchestrator/interface/observer 降为机制（scheduler/interface-gateway/metrics-aggregator） |
| ADR-0008 AR-9 "in_team_check.checkers" | 改 verification.test_authors + verdict_by=mechanism:verifier |
| ADR-0009 profiles v1（forbidden_* 黑名单/permissions_mode 双义/structural 字符串） | 全部由 v2 取代（白名单/isolation+approval 拆分/structural 三字段+CT） |
| ADR-0009 "duty_assurance: 别名≠builder（validate 强制）" | 升级为族级强制 |
| ADR-0007 "checker 评审计划" | 计划评审=代码校验+owner 批验收示例+premortem；checker 退出 |

## 分期

- **一期（本 PR）**：全部标准/声明/validate/门禁/CODEOWNERS/ADR；deployer/responder 原型就位（实例随首个生产团队组建落盘）。
- **二期**：hidden holdout 独立仓；pr-identity-path-matrix required check 实装（产品仓模板）；事件哈希链存储；gateway per-run 虚拟 key 配额实配；ruleset require_code_owner_review 开启（本 PR 合并后即配）。

## 后果

- 正面：5 处矛盾消除；fail-closed；出题判卷分离；意图保真与逃逸闭环补位；平台锁落地；控制测试让 structural 从断言变为持续验证的事实。
- 负面/成本：原型体系复杂度上升（9 LLM+6 机制+owner）；test-tree 冻结流程对小型 doc 变更有仪式成本（由 change_classes 分级吸收）；holdout 二期才有。
- 风险：机制原型的实现质量成为新的单点（scheduler 状态机/evidence-pack CI）——纳入 adversary 控制测试范围。
