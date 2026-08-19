# ADR-0014: 组织级流程显式化——意图路由、验收三分法与维护回路

- status: proposed
- date: 2026-08-18
- deciders: owner + AI
- 系列: PR-A（本文件；原编号 0013，因 #10 红队批次已用 0013 顺延——编号唯一性检查强制）/ PR-B（owner 控制与可观测）/ PR-C（场景声明化与测试引擎统一）
- 前置: ADR-0011（团队协作 v1.0）、ADR-0012（schema 对齐与 check 注册表）

## 背景

团队协作标准（怎么流）与原型标准（谁来做）定稿后，缺最后一层：**owner 的嘴怎么接进机器**。
具体四个问题（owner 原话）：

1. 我下达意图到最后完成，流程是什么？
2. 持续代码质量管理和仓库治理——每周扫描发现问题，是我手动启动 agent 修吗？
3. 新仓库启动是怎样的？
4. 我有个小地方要修，是直接起 worker 还是必须按流程走？

讨论中确立的核心判断：**讨论组织流程，本质是"人类意图有哪些，它们如何被组织承载"**。

## 决策

### 1. 意图八分类路由表（standards/intent-routing.yaml）

deliver / fix / respond / investigate / maintain / govern / spawn / ask——每类声明
{载体, 验收来源, owner 同步成本, flow_ref}。三条组织立场：

- **R1 不设多套流程**：只有一台状态机（team-collaboration 相位机）+ 多个入口重量。
  意图分类是路由表不是新流程——差别只在验收标准从哪来、走多重的门。
- **R2 owner 从不启动任何东西**：触发只有三种（意图/事故/时间到）。分类由
  interface-gateway 按路由表机制判定，owner 说人话不说类别；歧义按"更重一侧"路由
  并确认一次（默认动作=问，不猜）。
- **R3 注意力只花在"新对错"上**：验收三分法（下）是路由表的经济基础。

### 2. 验收标准三分法（flows.yaml#intent_ratification.shortcuts）

| 来源 | 语义 | 适用 | owner 成本 |
|---|---|---|---|
| new_ratable 新批 | 定义新的"对" | deliver | 批示例（账本同步点） |
| self_evident 自明 | "对"在意图出口时已定义完 | fix/trivial | 0（下达即全部） |
| pre_approved 预批准 | 批准检查时已预批未来复绿 | maintain/spawn 基建 | 0（一次性发生在过去） |
| predetermined 预声明 | 载体声明写死（exit_criteria/ADR） | respond/govern | 按账本 |
| evidence_based 证据 | 问题被证据回答即合格 | investigate/ask | 0 |

guard：自明的升级例外照常（trivial.promote_if 路径规则）；预批准不可迁移到新验收面
（drift 复绿预批的是"回到期望状态"，不是"期望状态改变"）。

### 3. trivial 与 spike 载体类（change-classes.yaml）

- **trivial**（fix 载体）：自明验收、无波次排程、verifier 判卷不豁免。**为什么不设
  "小修免检直通"**：反仪式膨胀的对偶是例外膨胀——"小修"定义必然膨胀（人会把自己的
  卡叫小修）。判卷是机器成本不是注意力，不省它。promote_if 四条路径规则机制判定升级。
- **spike**（investigate 载体）：无合并面，产 ADR/finding；evidence_based 验收；
  结论必须附引用（findings.json sources minItems:1 已锁）。摸底发现 spike 此前无载体
  类，是真实缺口。

### 4. 维护回路（flows.yaml#maintain_loop）——"周扫发现问题怎么办"的结构答案

issue 生命周期五态：open（扫描器自动开）→ triage（curator 周审转 backlog.proposals）
→ consumed（planner producer_gate 必处置 top-k）→ closed（修复 PR 关 issue + 复绿证据）
/ deferred（唯一豁免出口：机器可判定条件 + 理由 + aging 可见）。

不变式：**issue 不可能躺在列表里**——要么消费、要么显式驳回、要么 deferred 带条件，
三选一强制无第四态；deferred 条件到期自动重排（豁免也有保质期）。

maintenance_wave（owner 不下新意图时的自救通道）：backlog 存在 security 级条目 OR
aging 最老条目 > 30d → curator 提请 delivery_squad 以 backlog 为波次范围组建；
验收 pre_approved。**owner 唯一接触点是周审（asynchronous，默认略过留痕）**。

### 5. spawn 与小修的直答

- 新仓：spawn 意图 → new_repo 机制链（GOVERNANCE flows.new_repo：template 建仓→
  init 防线→REPOS.yaml 申报→骨架 PR）→ 首模块转 deliver。基建=模板即验收（pre_approved），
  owner 只批首模块示例（new_ratable，1×）。
- 小修：说意图，机制路由 trivial 单卡——自明验收→builder→verifier 判卷→自动合并，
  全链无人阻塞。会停的只有两种：触及 dep/schema（owner_ratify 异步）；verifier fail
  （那是修错了，不是流程重）。

## 后果

- intent-routing 成为组织级流程的单一入口声明；validate fail-closed（路由引用的
  change_class/团队原型必须存在；trivial/spike 不可成孤类）。
- 注意力账本零新增：trivial/maintain/spawn/ask 均无新阻塞点（核对过 attention-ledger
  现有条目覆盖）。
- 代价：intent-routing.yaml 本身是 C1 资产（改路由表走 PR+ADR）——路由是组织分叉点，
  变更成本理应高。
- PR-B（后续）：owner 控制（pause/resume/abort）+ 可观测性（TUI 视图/agent 查询/log 分级）。
- PR-C（后续）：场景声明化 + 模拟器引擎化 + CT scenario 链接——测试底层方法统一
  （事件进/事件出/断言不变式）。
