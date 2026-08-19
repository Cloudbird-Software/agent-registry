# ADR-0016: 红队演练二批修复——三治仓声执一致性与漂移检测盲区

- status: accepted
- date: 2026-08-19
- deciders: owner + AI
- resolves: CI-Workflows #6 / agent-registry #18 #19 #20 / .github #45 #46 中经独立复核**确认属实**的子项（伞决策，跨仓落地）；不属实项以证据逐条驳回（见"复核结论"）
- cross-repo: Cloudbird-Software/.github（schema/GOVERNANCE/drift-check 批次）、Cloudbird-Software/CI-Workflows（zizmor/adr-required/版本策略批次）

## 背景

红队第二批报告（三仓五 issue，79+ 项）以"客观证据"自居，但**红队证据≠事实**——本批修复前逐项独立复核：部分属实、部分已在先前批次修复（红队扫的是旧树）、部分因只做静态 grep 误读平台侧实现、部分与有意设计冲突。

## 复核结论（属实→修，不属实→驳）

**属实（本 ADR 决策修复）：**

1. CI-Workflows README 声明"gate adr-required 检查"但 ci.yml 无此步骤——声执不一致（红队 #6 关联、.github #45 结构性问题的实例）。
2. CI-Workflows zizmor.yml 的 `unpinned-uses.ignore: [ci.yml]` 豁免理由（"ci.yml 自引用 @main 不 pin"）已失效——现树 ci.yml 零自引用、全部 uses pin SHA。死配置=未来 ci.yml 引入未 pin uses 被静默放行。
3. v1 浮动大版本指针无完整性检测（CI-Workflows #6-A）：admin 可强移 v1 改变全部业务仓实际执行的 gate 内容，且无任何每日检测会发现。
4. event.schema v1 仅 5 类事件（agent-registry #20）：handoff 审计（AR-6）、审批流、凭据使用、预算熔断、团队生命周期均不可追溯——AR-7"事件流是审计支柱"覆盖不足。
5. team.schema/GOVERNANCE AR-6 措辞"handoff **全部**完成才允许销毁"与单一真源 team-collaboration.yaml 语义不一致（agent-registry #18 内核）：真源规定销毁前置=after-handoff(**team_side**)，stewardship_side 项（memory-distill/adr-write 等）由 curator 异步消费归档资产执行、**不阻塞销毁**。措辞错位制造了"owner 依赖项卡死归档"的假想死锁。
6. drift-check §10 仅验被引 ADR **文件名存在**（.github #45 RB-D5）：空文件/占位文件同时骗过 gate 与 §10，"有 ADR"退化为"文件存在"。
7. governance-drift.yml 漂移 issue 评论无去重（.github #46 RB-B2）：同一漂移每日追加评论，issue 无限膨胀。

**驳回（证据见各 issue 回复）：**

- agent-registry #19（builder↔test-editor 互斥仅文档）：`archetype` 是**单值 enum**——"同一声明双原型"结构上不可能，if/then 无从约束；跨声明的 team 级利益分离已实装（validate.py "既是 builder 又是 test_author"分支）且族级独立已实装（同文件 models.yaml family 全局比对）——issue 引用的行号是 archetype **职责说明注释**，非约束声明。元验证测试套件（ADR-0013）已覆盖"验证器被篡改"担忧。
- CI-Workflows #6-C（无 timeout）：全部 6 个 workflow 均有 `timeout-minutes`（PR#5 已修，红队扫的旧树）。
- CI-Workflows #6-D（无 CodeQL）：CodeQL 走 **default setup**（平台侧，`code-scanning/default-setup` state=configured，languages=[actions]），静态 grep 仓内 workflow 自然看不见。
- .github #45 P0-05（族级独立未实现）：validate.py 已有族级全局比对（"同模型族"FAIL 分支）。
- .github #45 P0-14（§8 正则可伪造）：§8 已改为**唯一权威判据=关联 PR API**，显式注释"后缀可伪造，不做消息预筛"。
- .github #45 P0-19（标题模糊搜索）：governance-drift.yml 已改专属 label `auto-drift-report` 归属判定。
- agent-registry #18 建议的 `handoff_timeout`/`force_destroy` 降级路径：与有意设计冲突——incident_cell"到期绝不 auto-destroy、冻结现场持续升级"是安全优先的设计决策（team-collaboration lifecycle 注释显式声明）；正确修复是措辞对齐（见决策 5），不是给冻结语义开洞。

## 决策

1. **CI-Workflows adr-required 实装**：ci.yml gate job 增 adr-required 步骤（移植 .github gate.yml 同模型；C1 路径模式=\.github/、zizmor\.yml、README\.md——本仓现存的全部受管资产，新增受管路径须同步扩模式；--paginate 拉文件清单；词边界 ADR-NNNN 匹配；存在性由 .github drift-check §10 后验——不在 PR 上下文注入 org secret，zizmor secret-exposure 模型）。checks.yaml adr-required where 增 CI-Workflows 执行点。
2. **zizmor 死配置清理**：删除 unpinned-uses ignore——现树零自引用，豁免无对象；未来未 pin uses 应当报错而非豁免。
3. **v1 指针完整性检测**（drift-check 新 §11）：每日校验 `refs/tags/v1` 指向 commit == 最高 v1.x.y tag 指向 commit；不一致=漂移（admin 强移指针 24h 内检出）。README 版本策略同步改写：移动 v1 须在 PR 合并后由**另一只手**（另一个 session/终端）复核 tag 指向再推——发布流程从"备忘录"升级为"可检测不变式"。
4. **event.schema v1.1**：事件枚举扩至 11 类——原 5 类 + handoff_step / approval / credential_used / budget_consumed / team_lifecycle / judge_verdict（payload 各入 $defs；requested/granted/denied 等子态并入 payload 枚举，避免顶层类型爆炸）；版本 $id @1.1（枚举只增不破，向后兼容）。
5. **AR-6 措辞对齐**：team.schema handoff 描述与 GOVERNANCE AR-6 intent 改为"**team 侧** handoff 全部完成才允许销毁；stewardship 侧项由 curator 异步消费归档资产执行（destroy_scope：数据层制品/事件不随队销毁）"——与 team-collaboration.yaml 单一真源一致，消除假想死锁。
6. **§10 ADR 实体性校验**：幽灵 ADR 检查从"文件名存在"升级为"存在且非空"——被引 ADR 文件 size < 阈值（1 字节即空文件）= 漂移。
7. **漂移评论去重**：漂移指纹=报告全文 sha256（跨 run 稳定——同一漂移内容不变则指纹不变，run_id 仅作执行元数据随文附带）；开评论前比对最近 10 条评论的指纹标记，指纹已存在即跳过。幂等语义=漂移内容不变不重复报、漂移内容变化（新指纹）必报。

## 后果

- 三治仓"声明 vs 执行"缺口（README 声明的检查、schema 声明的语义）全部闭环或显式登记。
- v1 指针从"信任 admin 不犯错"变为"错了 24h 内响铃"。
- 事件流可支撑 handoff/审批/凭据/预算审计——AR-6/AR-9 的审计支柱有了数据形状。
- 代价：CI-Workflows 此后所有 PR 须引用 ADR（本就属 C1 声明，只是补上执行）；v1 发布流程多一步复核。
- 红队二批不属实项以证据关闭，防"报告即事实"的修复冲动污染治理语义。
