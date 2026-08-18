# ADR-0009: archetype 内部构成与职责保证——profiles 机制

- status: accepted
- date: 2026-08-18
- deciders: owner + AI

## 背景

十原型确定后（ADR-0008），需要回答：每个原型作为一种"功能节点"，其**内部由什么组件构成**、**靠什么确保自己称职**。agent 内部不止提示词与记忆：还有内部流程、嵌套 agent-as-tool、guardrails、权限面、凭据、I/O 契约。若每个 agent 各自随意组合，原型的语义会被稀释。

## 决策

### 1. profile = 原型的内部结构标准

`standards/archetype-profiles.yaml` 为每个原型定义六要素：

- `mission`：该节点承担的功能
- `internal_flow`：内部流程骨架（agent.workflow / identity 提示词 / skill 的蓝本）
- `typical`：典型构成（模型档/记忆/工作区——指导性）
- `duty_assurance.structural`：**结构性保证**——权限/组件裁剪使失败"不可能"或"必然留痕"
- `duty_assurance.verified_by`：**验证性保证**——谁用什么客观证据判定它称职
- 机器强制字段：`requires` / `permissions_mode` / `forbidden_tool_effects` / `forbidden_agent_tool_archetypes`

职责保证的统一哲学：**结构性保证优先于验证性保证**——能靠权限裁剪让失败不可能，就不依赖事后检查；必须有事后检查的，证据必须客观可回溯（mutation score、事件流、引用链），绝不依赖 agent 的自我评价。

### 2. agent 声明新增两个内部维度

- `capabilities.agent_tools`：agent 内部可调用的 agent-as-tool（`agent:<id>` 引用）。此前 agent-as-tool 只在 team 装配层（members.as_tool）表达，现补齐 agent 运行时内部消费的声明位。受原型限制：如 builder 禁引 checker/judge（防自证/施压），judge 全禁（判决只读原始材料）。
- `workflow`：agent 内部流程。`mode: fixed|autonomous`（计划者/检查者/仲裁者=固定流程；构建者/检索者=自主+约束），`steps_ref` 指向 registry 内流程文档，`entry_skills` 声明入口技能。

### 3. 可执行标准随校验器同仓

profiles 落 agent-registry/standards/（非 .github/standards/）：validate.py 在 CI 消费它，跨仓拉取会引入网络脆弱性与 submodule（已否决）。声明 schema（什么是合法声明）仍在 .github；执行性标准（怎么被强制）随校验器。两者都以 PR+ADR 治理（本文件即 C1 凭证）。

### 4. validate.py 强制清单

- profile 缺失该原型 → 拒绝
- `requires` 点路径为空 → 拒绝（如 builder 无 must_run、researcher 无 expose.as_tool）
- `permissions_mode` 不符 → 拒绝（judge/checker/operator=strict）
- 工具副作用 ∩ `forbidden_tool_effects` ≠ ∅ → 拒绝（如 judge 禁 shell/写/网）
- `agent_tools` 引用被禁原型 → 拒绝
- 附：agent_tools 引用存在性+状态门禁；prompt_ref / steps_ref 文件存在性

## 后果

- 新 agent 声明 = 选原型 → 按实例化 profile 补组件 → 校验器保证不合规者进不了 registry。
- 十个原型的其余五个（orchestrator/curator/interface/observer/operator）尚无实例条目；profile 已就位，实例化时按图组装。
- identity 提示词（5 份）与固定流程 steps（2 份）随本 ADR 落盘，与 profile 蓝本对应。
