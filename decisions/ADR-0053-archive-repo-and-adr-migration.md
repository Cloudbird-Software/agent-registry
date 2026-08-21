# ADR-0053: archive 记忆层仓与旧 ADR 归档迁移（W1-C1）

- status: accepted（2026-08-21）
- deciders: 人（owner randypanding）+ AI
- 关联: .github#164（W1-C1 工作卡）、宪法 specs/IR-0003/constitution.md §1（记忆层/拆家原则）、§13 推论二（数据飞轮）、.github#96（ADR 实质校验——索引格式为其预留扩展点）

## 背景

宪法 §1 定层：`archive` 仓 = 记忆层（废止/全部 ADR 正本、规划回归集、事件 JSONL、
红队报告——后三类随后续波次落位），变更规则 append-only；§13 推论二将记忆层升级为
战略资产（训练与评估飞轮的原料库）。拆家原则明确"旧 ADR 不删除，标
`active/superseded/archived` 迁记忆层"。

现状缺口：agent-registry/decisions/ 已积累 52 个 ADR（ADR-0001~0051，含 ADR-0011
历史双档），全部为平铺正本——无生命周期标记、无归档层，与宪法 §1 记忆层设计不符；
本卡（W1-C1）负责建立 archive 仓并执行首次全量迁移。

## 决策

1. **新建 `Cloudbird-Software/archive` 仓**（public，L1 记忆层，append-only）：
   - 只增不删不改；历史文件永不 rewrite；异地备份注记（宪法 §10.1 供应链单点
     缓解——关键产物可异地备份，archive 属关键产物）。
   - 目录约定 `adr/` = ADR 归档正本（字节保真，见决策 2）；状态标记不写在
     archive 文件里（保持与源逐字节一致），唯一真源 = 决策 3 的墓碑索引。
   - 建仓 bootstrap README commit（org admin bypass 直推）登记
     expected-state.json direct_push_exemptions。
2. **字节保真 + 状态在索引**：迁移 = decisions/ADR-NNNN-slug.md 逐字节复制到
   archive/adr/（sha256 证明，AC-1"逐条 diff 校验"的机器形态）；文件内容零改动
   （不做 status 改写、不加迁移头）——归档正本即历史原件，任何改写需求一律新开
   ADR。生命周期（active/superseded/archived）与 decision_status（原文
   accepted/proposed）登记于墓碑索引，不污染正本。
3. **墓碑索引 = `agent-registry/decisions/INDEX.yaml`**（机器可读，随 ADR 同仓
   同 PR 治理）：`version/source_commit/migrated_at/entries[]`，每 entry 含
   number/title/file/lifecycle/decision_status/archive_path/content_sha256，
   superseded 条目带 superseded_by + rationale。**新 ADR 的落位流程自本 ADR 起
   变更：正本入 archive/adr/ + decisions/ 落墓碑 + INDEX.yaml 登记 entry（同一
   PR 或紧随 PR 完成，INDEX 缺登记 = gate adr-required 索引世界 fail）**。
   - 索引格式为 #96（ADR 实质校验）预留扩展点：entry 可扩展
     `substantive: {h1, sections}` 等字段；#96 落地时消费，本 ADR 只锁骨架。
4. **decisions/ 留同名墓碑**（编号可解析性）：原文件名不变、内容替换为墓碑块
   （status/lifecycle/archive 链接/migrated 注记 + 一句话决策摘要）。文件名保留的
   原因：org-gate（钉版 v1.4.2）与 .github gate.yml 的 adr-required 均按
   **文件名前缀**校验 decisions/ 清单——墓碑保留原名则两个关卡零改动通过存在性
   校验（零级联）；实体性（内容结构）校验只有 drift-check §10 消费，由决策 6
   单点切换内容源。
5. **双世界兼容**：INDEX.yaml 存在 = 索引世界（gate/§10 经索引解析 archive 正本）；
   不存在 = 旧世界（现清单+本仓内容逻辑原样）。迁移 PR 合并前置 =
   .github 索引感知 PR 已合并 + 全部 W1 ADR 已落 decisions/——顺序错误产生的
   窗口内，旧 §10 对墓碑会误报"空壳"，故合并序不可颠倒。
6. **关卡改造（.github 仓 PR）**：
   - gate.yml adr-required：先试拉 decisions/INDEX.yaml，200 → 索引世界（被引
     ADR 须在 entries 且 archive_path 非空 + archive 正本 HEAD 可达）；404 →
     旧世界原逻辑；INDEX 拉取失败 fail-closed；引用不存在编号两世界均 fail
     （防幽灵 ADR 语义不回归，#164 AC-2）。
   - drift-check.sh §10 adr_substantive()：内容源切换——INDEX 存在时从 archive
     raw 拉正本做既有结构校验（H1 编号/status/背景/决策），INDEX 不存在走现逻辑。
7. **archive 仓 verify 工作流**（phase 2）：`scripts/verify_migration.py` 三断言
   ——(a) INDEX 每个 entry 的 archive_path 存在且 sha256 == content_sha256；
   (b) adr/ 无 INDEX 未登记文件；(c) INDEX source_commit 处 agent-registry 源文件
   sha256 == content_sha256（保真闭环）。PR+push+weekly 运行。

## 后果

- 正面：宪法 §1 记忆层落地；ADR 生命周期可机读（INDEX 三态）；agent-registry
  decisions/ 收敛为"索引 + 墓碑 + 未迁移新 ADR"轻量形态；org-gate/gate 零改动
  （文件名校验兼容）；#96 有扩展点可接。
- 负面/成本：新 ADR 流程多一步（archive 正本 + INDEX 登记）；archive 成为 ADR
  可达性的运行时依赖（gate 每 PR HEAD archive raw）——公开仓 raw 无鉴权，
  可用性风险接受，verify workflow weekly 兜底。
- 风险与回滚：迁移可逆——反向脚本按 INDEX.content_sha256 从 archive/adr/ 逐条
  恢复 decisions/ 正文（sha256 校验后写回），删 INDEX.yaml 即回旧世界（双世界
  兼容保证 gate/§10 无缝回退）；archive 仓 append-only，迁移正本永不删除。
