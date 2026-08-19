# ADR-0022: 注册层门禁硬化（issue #31 审计收敛）

- 状态: proposed
- 日期: 2026-08-19
- 决策: 采纳 issue #31 审计报告的收敛判据 1–10，实装 validate.py 语义防线 + 声明侧对齐
- 影响: standards/side-effects.yaml、archetype-profiles.yaml、team-collaboration.yaml、
  attention-ledger.yaml、intent-routing.yaml、flows.yaml、scenarios.yaml、
  registry/agents/*、registry/schemas/*、standards/control-tests.yaml、scripts/validate.py、
  tests/test_validate.py

## 背景

issue #31（独立审计，基准 `55818ef`）以 18 组可复现变异实验证明：两条 CI required
门禁（validate + simulate）对 14 组声明缺陷放行。当前 HEAD（ADR-0021 合并后）复测
15/15 变异仍双绿——snapshot-diff（ADR-0021）只能拦"未同步 golden"的篡改，随 golden
一并提交的语义违规无语义层防线。

核心缺陷（审计编号沿用 issue #31）：

- **A-1** `capability-whitelist(validate)` 在代码中不存在：`agent.allow ⊆ profile.allow`
  从未被校验，K–Q 七组越权变异（builder+vcs_merge / curator+vcs_admin / judge+写路径
  等）双门禁全绿——29 条 CT 的前提与 side-effects 的"不授予任何 agent / 唯 owner
  持有"约束在 registry 层零保护。
- **A-4** `deadlock_check` 因 `from: any` 通配边恒真（validate.py 旧 L109），
  相位图删到只剩一条边也不报。
- **C-1/C-2** verify 相位两条出边全依赖 `review.*`，而 doc/trivial 类 review=none、
  spike=curator、dep/schema 另需 `owner_ratify`（无生产者）——四类变更按
  change_class 分类死锁，无任何门禁建模。
- **A-2 变异 A/B/E/F/G/I/J** must_run×工具、事件生产者×座位、check 降级、
  输出 schema 语义、场景断言掏空均无防线。
- **B-2/B-5/B-6/B-7** deployer must_run 无执行面；adversary 无凭据声明（13 条
  adversary-executed CT 物理不可执行）；curator"提案权"无 registry 表达；
  arbiter fixed 无 steps_ref / reviewer.steps.md 孤儿。
- **D-3/D-4/D-5** flow_ref 从不校验且 govern/spawn 指向不存在的 governance/；
  注意力账本统计类别数却叫 per_week；wave-plan card 缺 trace_id（链路断裂）；
  JSON Schema 语法不被校验。

## 决策

### 1. validate.py 实装语义防线（不可随 golden 越过）

1. **capability-whitelist**：`agent.capabilities.allow ⊆ profile.capabilities.allow`
   且 `profile.allow ⊆ 词表`（K–Q 全拦；CT-BLD-002/PLN-002/JDG-001/CUR-001/RSP-001/
   DEP-001/RES-001 的声明层强制落地）。
2. **must_run 执行通道**：命令形态项（如 `make check`）⟹ 持 shell 类工具；
   `check:` 前缀项 ⟹ 已注册于 checks.yaml（变异 A 拦截；B-2 修复）。
3. **allow 执行通道覆盖（双向）**：side-effects.yaml 显式声明三通道词表
   `tool_required / platform_direct / runtime_builtin`——allow 中 tool_required 词
   必须有工具承载；platform_direct（ops API，ADR-0021 立场）与 runtime_builtin
   （编排层内建）为显式豁免登记（issue 收敛判据 9）。
4. **event_producers 引用解析**：`seat:X` ∈ seats、`mechanism:X` ∈ 机制原型、
   `agent:X` ∈ agents（变异 F 拦截）。
5. **场景断言载体非空**：每场景 asserts 或 hook 至少其一 + 声明式断言总数
   ≥ `scenarios.registry.asserts_floor_total`（变异 E 拦截——掏空场景即 fail）。
6. **check 降级防护**：id 出现在本仓 CI 执行点（.github/workflows step）的 check
   必须 active（变异 G 拦截）。
7. **test-author 输出语义**：输出 schema 禁判决字段且 $id 非 verdict 族
   （变异 I 拦截；CT-TA-004 升级 validate-executed）。
8. **profile.io_guarantees**：planner 声明 `output_must_have: [cards, …]`，
   validate 校验输出 schema 覆盖（变异 J 拦截——契约链断裂可判）。
9. **deadlock 修复**：`from: any` 边不计为具体相位出边；非终态相位须有
   `from == <phase>` 的边（变异 R 由 validate 而非仅模拟器拦截）。
10. **per-change_class 可达性求解**：按 `verdict_layers.review.dispatch` +
    event_producers 推导每类可用事件集，从 plan 出发断言 handoff 可达
    （C-1 分类死锁灭绝；收敛判据 8）。
11. **merge_policy/审查类 token 有主**：merge_policy 与 change-classes.review 引用
    的 `owner_*` 钥匙须 ∈ event_producers（C-2：owner_ratify 补生产者）。
12. **flow_ref fail-closed**：`file#anchor` 须实存且锚可解析；`external:` 前缀
    须在 intent-routing 的 `external_flow_refs` 豁免清单登记（D-3）。
13. **JSON Schema 语法校验**：registry/schemas/*.json 须可解析且结构合法（D-5）。
14. **workflow 绑定**：`mode: fixed` ⟹ steps_ref 必填；workflows/ 无孤儿（B-7）。
15. **adversary 凭据声明**：存在 adversary-executed CT ⟹ adversary 实例须声明
    `credential.impersonation`（B-5 声明层）。

### 2. 声明侧对齐

- **相位图**：`verify→integrate` 改 `gate.pass AND (review.approve OR review.waived)`；
  event_producers 增 `review.waived`（mechanism:card-gate，dispatch 判定 doc/trivial）
  与 `owner_ratify`（owner，dep/schema 第三钥）。
- **review dispatch 表**（verdict_layers.review.dispatch）：doc/trivial=waived、
  logic=test_author、spike=curator（入库审核）、dep/schema=test_author+owner_ratify、
  prod=test_author+owner_per_action（integrate 后）。channels.acl review.* 写者
  增 curator（限 spike 入库 PR）。
- **card_gate.requires 条件化**（C-3）：testability_signoff/test_tree_sha 仅
  acceptance-face 类（change_class ∉ [doc, trivial]）——trivial 快车道与卡门互斥消除。
- **B-4**：新增 schemas/review-decision.json（review 裁定事件的 payload 契约——
  合并第二钥匙的输出形状显式化）。
- **B-5**：red-adversary 声明 `credential.impersonation`（平台签发目标原型一次性
  凭据副本，作用域=真实凭据，用后即毁）；profiles adversary internal_flow 的
  "冻结相关流程"与 steps.md 对齐为"发 freeze 建议标志"。
- **B-6**：curator-main 对 tool:write_file 增加 standards/|scripts/|CODEOWNERS
  deny——"提案权"获 registry 层表达。
- **B-7**：新建 workflows/arbiter.steps.md 并绑定；reviewer.yaml 补 workflow 块。
- **C-4**：maintain_loop.issue_lifecycle.open 的扫描器枚举显式化（外部带外依赖）。
- **D-1**：CT-TA-004/CT-CUR-001/CT-RES-001 升级 validate-executed（3→6 条机器执行）。
- **D-4**：账本键 `max_synchronous_per_week` → `max_synchronous_categories`
  （守恒的是类目数；频次由类目语义界定并在 metrics 周报可审计）；
  ambiguity_rule 澄清并入 intent_ratification 类目预算（非账外点）。
- **D-5**：wave-plan.json card 增 trace_id（planner→builder 链路闭合）。
- **D-2**：机制原型已在 archetype-profiles 声明+id 绑定+幽灵检测（ADR-0021）；
  供应链清单管开源依赖，org 内部机制不适用——projects.yaml 注释显式声明边界。

### 3. 不修（有意保留）

- **A-5**（C1 型 PR 跳过 base 侧门禁）：documented tradeoff——C1 PR 的规则与数据
  必须同源演进（base 旧规则审 head 新数据在词表演进上不可行）；防线=CODEOWNERS
  owner-only + adr-required + head 双跑 + snapshot-diff 语义差分评审。
- **B-1**（给 incident_cell 塞 bash 工具）：按 ADR-0021 platform-direct 立场，
  infra 动作走平台 ops API（凭据/审计由平台承载）；本 ADR 以三通道词表将此
  设计显式化、可校验化，而非回退到工具面。

## 验收（issue #31 收敛判据对照）

1. K–Q 任意一组 → validate 退出码非 0 ✓（防线 1）
2. 变异 A → validate 报错 ✓（防线 2；B 按 platform-direct 显式豁免，见决策 3）
3. 变异 E → 断言下降门禁失败 ✓（防线 5）
4. 变异 F/G/I/J → 被拦 ✓（防线 4/6/7/8）
5. 变异 R → validate 报 deadlock ✓（防线 9）
6. `grep -c flow_ref scripts/validate.py` > 0 且外部引用显式豁免 ✓（防线 12）
7. `owner_ratify` ∈ flow.event_producers ✓
8. 每 change_class 可达 handoff ✓（防线 10）
9. `∀ agent: allow ⊆ ∪tool.side_effects ∪ 显式豁免通道` ✓（防线 3）
10. validate-executed CT 3→6，其检查在 validate.py 实装 ✓
