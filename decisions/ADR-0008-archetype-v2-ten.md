# ADR-0008: archetype v2——补 planner/judge/researcher，十原型封顶

- status: accepted
- date: 2026-08-18
- deciders: owner 质询 + AI 独立回复

## 背景

owner 三个质询击穿 v1 七分类：
1. 工作任务的源头是谁？人类只给意图，谁定波次/设计测试/写工作卡？谁保证 `make check` 真有效？
2. 遇到决策分歧怎么办？不可能事事上升人类。
3. researcher 可加；且听说模型可专门作 tool 干"找代码翻文档"，省 worker 上下文。

## 决策

### 1. planner（认同，从 orchestrator 拆出）

- 边界：**planner=设计时**（意图→波次计划+工作卡+测试规格），orchestrator=运行时（分派/监控/汇总）。混在一起会让"既排计划又管执行"失去制衡。
- 工作流位置：planner 产计划 → **计划须过 checker 评审**（防弱标准）→ checker 按规格**编写真测试代码**（测试作者权归 checker，builder 永不写自身验收——no-self-test 的组织级延伸）→ builder 实现 → checker 判决。
- checker 相应扩权：可写 tests/** 不可写实现（路径级权限分离，tiered_policy pattern 可执行）。
- **make check 有效性的元答案**：不靠"再多加一个审查者"（审查塔无限回归），靠客观指标短路——mutation score（testing.yaml T-10）验证测试杀变异能力，差分测试（T-09）验证行为等价。测试好不好，指标说话。
- 新约束：planner 与 builder 不得同一声明（标准制定者不可施工）。

### 2. judge（认同，但严格划界）

- 管辖权来自团队声明的授权域（枚举：测试抖动判定/评审分歧/规格歧义解释），**越域即改判"上升人类"**；治理/安全/生产动作永远人类（RL-1）。
- 独立性：validate 强制仲裁者模型别名与争议双方（builder/checker 成员）均不同——不能是任何一方同脑。
- 判决=结构化输出（decision+rationale+jurisdiction_basis），落 decision_made 事件形成判例库；owner 可推翻任何判决（破玻璃同哲学）。
- 升级阶梯：组内分歧 → judge（域内，自动）→ owner（域外/政策/生产，唯一人工口）。

### 3. researcher（认同，as_tool 是关键形态）

- 权限特征：读外部网络+读任意仓库，只产结构化报告（每条结论带 source 引用），不写仓库不碰生产。
- **上下文经济**：以 `expose.as_tool: true` 被 builder/planner 调用——全文留在 researcher 自己的上下文，worker 只收结论+引用。这正是"模型作为 tool 翻文档找代码"的机制化，schema 原生支持（io_contract 约束往返体积）。
- 修正一处设计错误：agent-as-tool 消费发生在 team 组装层（members.as_tool），agent 的 capabilities.tools 只收 tool: 注册项。

### 4. 克制：拒绝清单（十原型封顶）

| 拒绝加 | 理由 |
|---|---|
| critic | =checker（验收判决） |
| negotiator | =orchestrator 的协调协议，非信任边界 |
| memory-keeper | 记忆属 agent.memory + 事件流，非角色 |
| auditor | =curator（治理审计）+ judge（分歧裁决）组合 |
| teacher/trainer | 技能演进=Skill 自演进机制 + handoff.skill-extract，非角色 |

**封顶规则：提出第 11 个原型必须走 ADR，论证其权限/凭据/审计特征无法被现有十类覆盖。**

## 后果

- schema enum 十项；validate 增 judge 独立性强制；registry 增三个 proposed 条目（wave-planner/arbiter/researcher-code，未经实战，首引用时提级）+ web_search 工具。
- planner 用的 planning skill、judge 管辖域的正式枚举 → 留待 teams 轮（下一轮讨论）定义。
- GOVERNANCE AR-8 intent 同步更新。
