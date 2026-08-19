# ADR-0015: 场景引擎与测试底层方法统一

- status: proposed
- date: 2026-08-18
- deciders: owner + AI
- 系列: ADR-0013（现 0014）系列 PR-C；本 ADR 原编号 0014，因编号顺延改 0015
- 前置: ADR-0011（simulate-wave 12 场景）、ADR-0013（意图路由/owner 控制/维护回路）

## 背景

流程、角色、治理都已声明化之后，owner 提出：**流程本身也需要是声明式的；做出来要考虑
如何模拟、未来流程怎么测试；测试的底层方法要代码化、要统一**。

现状：simulate-wave.py 的 12 场景内嵌在 Python 函数里——场景不可 diff、不可 PR review、
新增场景必须写代码；CT（control-tests.yaml 29 条）是手册式登记，无场景链接——
"控制测试是否可执行"无法机器判定（ADR-0012 已发现 adr-required 是假防线的实例）。

## 决策

### 1. 统一方法论：一切测试 = 事件进 → 事件出 → 断言不变式

组织的一切行为是状态机的转移；转移可枚举 → 可测试。三层：

- **L1 断言原语**（A1-A7，不变）：actor 存在 / 权限合法 / 注意力有账 / 预算有归属 /
  事件有生产者 / 相位转移合法 / 留痕完整——全场景共用，这是"底层方法统一"的"统一"
- **L2 场景剧本**（standards/scenarios.yaml，本 ADR 核心变更）：每场景
  {id, class(regression|control), narrative(事件序列走查), asserts(声明式断言), hook(可选)}
- **L3 门禁**：PR 跑回归场景；CT 声明层先决跑 control 场景；运行时攻击面 adversary 执行

### 2. 声明式断言（引擎求值，零 Python）

```yaml
asserts:
  - {path: "standards/flows.yaml#owner_control.verbs.pause.semantics", op: contains, value: wall_clock}
```

op ∈ {exists, eq, contains, not_contains, contains_all}。新场景**优先纯声明式**——
S13-S17（trivial 直通 / maintain loop / maintenance wave / owner pause-abort /
未批意图拒绝）全部零 hook 落地，证明声明化可行。复杂跨结构推导（如授权矩阵 ⊆
responder.allow 的集合比对）保留 hook（S1-S12 存量）；迁移到纯声明式=后续增量，
不假装一次完成。

### 3. CT 双层链接（"假防线"从无法发现变为机器可判）

每条 CT 增两字段：
- `scenario`：**声明层先决**场景（模拟器绿 = 该 CT 的前提声明成立；null=无场景覆盖，
  须显式）
- `runtime`：运行时执行方式 ∈ {adversary-executed(红队真试), validate-executed(校验器即
  执行), manual_only(须带 runtime_note 理由)}

29 条 CT 全部链接完成：10 条 adversary-executed（带场景先决）、3 条 validate-executed、
16 条 manual_only（每条带理由——多数是运行时凭据攻击面，模拟器测不到属诚实边界而非缺陷）。

validate 双向校验：CT 引用的场景必须存在；scenario.ct_refs 引用的 CT 必须存在；
manual_only 无理由=CI 拒绝。

### 4. 场景注册表驱动执行

simulate-wave.py 改为读 scenarios.yaml 驱动：注册表与 hook 双向一致性检查（声明
hook 不存在/实现未登记=漂移=FAIL）；输出按 class 统计。**新增流程的测试=新增 YAML 场景**
（纯声明式场景零 Python）——"未来流程怎么测"的答案。

## 诚实边界（写进 scenarios.yaml 头部）

模拟测"声明的世界"（权限/相位/预算/事件逻辑自洽）；实现的世界归 gate/verifier；
防线真实有效归 escape_review/CT。三层各管一段，不互相冒充。

## 后果

- 场景可 diff 可 review 可 PR——流程变更破坏可执行性时 CI 精确指出哪条断言红了
- "测试底层方法统一"落地：L1 原语 + L2 声明剧本 + L3 门禁，无第二套方法
- CT 从手册变半机器：声明层先决自动跑，运行时部分显式分类（16 条 manual_only 的理由
  本身就是攻击面清单——待自动化时逐条消灭）
- 代价：S1-S12 断言仍在 Python（hook）——声明化不彻底；迁移是增量工作，每迁一个
  场景断言数可数（当前声明式 30 条 + hook 12 个）
