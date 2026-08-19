# ADR-0021: 红队批次3修复与治理测试回路

- status: accepted（2026-08-19）
- 背景仓库: agent-registry / .github / CI-Workflows / template-service
- 关联红队报告: .github issues #64-#72、template-service issue #11（去重后共 10 份报告）

## 背景

四个治理仓在 2026-08-19 收到多轮红队流程演练报告。基线门禁（validate.py +
simulate-wave.py 20 场景）全绿，但报告揭示的问题分三类：

1. **声明层状态机死锁/矛盾**（本 ADR 决策 1-6 修复）：
   - planner `exit_on: cards.ratified` 退场后，handoff 相位的 memory-export 仍声明
     由 `seat:planner` 执行——死人执行者，ephemeral 队永不销毁（#67-1.2/#71）。
   - 纯 doc/spike 波次无发布面：`released_behind_flag OR reverted` 永不发生 →
     integrate→handoff 边不可达、destroy 永不满足——ephemeral 队泄漏（#67-24）。
   - owner 长期不可用：intent_ratification / sev1_forward_fix_authorization 两个
     synchronous 项无默认动作，与"无默认动作的人在环点禁止存在"自相矛盾
     （#67-1.1/#66-B/#72-P0-1）。
   - "retry 耗尽必须回 planner"只有文本承诺，相位图无 `retries.exhausted` 事件与
     回 plan 边；争议期 budget_clock 暂停使 retries 门禁可被争议循环绕过（#67-21/22）。
   - verdict_stalemate 只计"结论相反"，同向僵持永不计数 → judge 永不激活；builder
     主张"测试写错了"在 test_fix.initiator 枚举下无合法落点（#67-17/18）。
   - 边界公理允许"sev1 且回滚不可行→前进修复"与 sev1_data_integrity 禁 forward_fix
     矛盾；incident_cell owner 缺席时 TTL 到期只能滞留（#67-25/26）。
2. **声明层结构缺陷**（决策 7-8）：
   - 交付链 5 个机制（scheduler/verifier/integrator/evidence-pack/metrics-aggregator）
     被引用为执行者但无 services 块；`mechanism:gate` 无原型；同一实体三种写法
     （card_gate / card-gate / gate）靠模拟器硬编码桥接（#69-5/6/7）。
   - App 名漂移：GitHub App 实际 slug 为 cloudbrid-agent（API 实证），4 个 agent
     声明与 automerge 注释写成 cloudbird-agent（#71-A1）。
3. **跨仓治理断点**（由本 ADR 授权、在各仓 PR 落地）：
   - ruleset main-protection `require_code_owner_review=true` + `0 approvals` +
     单人 CODEOWNERS → 一切合并只能走 admin bypass，SC-3 依赖自动合并名存实亡。
   - GOVERNANCE.yaml GM-1 cron 声明 daily 03:00、实现为 hourly；BP-2/AG-3 引用
     不存在的 T-11；C1 scope 将 template-service 整仓圈入却无 adr-required 实装。
   - REPOS.yaml agent-tools 为 planned 但被 approved 工具引用（悬空供应链）；
     agent-registry key_paths 漏 standards/ 与 simulate-wave.py。

## 决策

1. **memory-export 执行者=handoff 相位在场座位**（delivery=test_author；planner 的
   规划经验经 cards/contracts 制品随 artifacts-pr 留存）。context-assembly
   memory.digest.producer 同步。
2. **no_release_face(wave) 谓词**：波次全部卡 change_class ∈ [doc, spike] 时，
   integrate→handoff 与 destroy 条件增加该出口（merge/入库即交接）。
   delivery scope may_touch 补"ADR 草案（仅 spike 卡）"消除 spike 产出与写域冲突。
3. **owner 缺席默认动作**（全部取"更可逆一侧"，绝不默认放行）：
   - intent_ratification：7d 未批 → 意图暂存回 backlog(pending_owner)，波次按
     abort(need_gone) 善后销毁。
   - sev1_forward_fix_authorization：24h 未批 → 维持保守稳态（actions_else/data_freeze）。
   - incident TTL 后 owner 仍不可达 72h → parked 出口（保守稳态交接 maintenance wave）。
   - amendment escalate owner 24h 未裁 → 默认整波回炉退 backlog。
4. **retries.exhausted 事件（producer=scheduler）+ any→plan 回炉边**；amendment
   during 注明 retries 计数不随 budget_clock 暂停。
5. **verdict_stalemate 判据扩展**：结论相反 OR 同向僵持经 1 轮 test_fix 仍不让步；
   test_fix 增加 builder_path（builder 主张测试有误→amendment_request 合法落点，
   test_author 不认 → 计僵持）。
6. **边界公理与事故授权对齐**：sev1 前进修复例外显式排除 sev1_data_integrity；
   deployer 座位三处口径统一为"实例常备绑定=预占座位，动作仅 sev1 前进修复且
   owner_required"。
7. **机制命名绑定单一真源**：services 块（下划线键）必带 `id`=archetype-profiles
   机制原型键（连字符），补齐 scheduler/verifier/integrator/evidence_pack/
   metrics_aggregator 五个服务块与 tui 原型；`mechanism:gate` 全部改为
   `mechanism:verifier`（gate 是判决层名不是实体）；`mechanism:git` 改 platform。
8. **validate.py 三项新防线**（fail-closed）：mechanism:X 引用必须解析到机制原型；
   services id↔键名互译；团队 services 列表必须解析到 services 块；approved agent
   必须有消费方（幽灵角色检测——红队实证 ghost 声明可通过旧门禁）。新增场景
   S21-S24（owner 缺席默认/无发布面销毁/重试耗尽回炉/机制完备）+ 5 个负向元测试。
9. **治理测试回路**（本 ADR 第二主题，见 PR 后续）：agent-registry 建立周期 Action
   （回归=validate+simulate+pytest 元测试；差分=声明面 golden snapshot 逐 PR 审阅、
   负向注入差分已由 pytest 承担；canary=消费四仓公开声明与线上可观察面的无凭据探测）。
   四仓 PR（.github ruleset/GOVERNANCE 对齐、CI-Workflows CODEOWNERS、
   template-service adr-required+push 审计+pin）均引用本 ADR。

## 后果

- 声明层消除 6 类死锁/矛盾；"声明的世界"与运行层的实体命名一一对应。
- 红队可复现的注入手法（ghost 机制/幽灵角色/悬空服务引用）从此在 PR 门禁被拒。
- 不做的事（显式记录）：运行时机制（scheduler/verifier 等）的实现仍按 ADR-0010
  二期节奏，不在本批次；owner 单点是一人公司的既定设计（ADR-0010），本批次只消除
  "等待失联者无终止条件"的无定义行为，不引入第二审批人。
