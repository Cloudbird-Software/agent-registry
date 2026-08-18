# ADR-0005: 软硬双层控制——AGENTS.md 管引导，权限引擎+凭据+CI 管强制

- status: accepted
- date: 2026-08-18

## 背景

AGENTS.md/提示词是软控制：LLM 可能不遵守。要真正限制 agent 行动，需要与模型无关的硬控制层。

## 决策

控制分五层，前两层为硬控制（LLM 无法绕过）：

| 层 | 机制 | 性质 |
|---|---|---|
| 1 供给侧裁剪 | agent 声明的 `capabilities.tools` 白名单：未声明的工具对 agent 不可见 | 硬 |
| 2 运行时权限引擎 | tiered_policy（allow/ask/deny × severity × 参数 pattern），在编排框架内拦截 | 硬 |
| 3 凭据最小权限 | per-agent/per-team 作用域 token；无权限=物理不可能（如 reviewer 无 push 凭据路径） | 硬 |
| 4 平台防线 | 分支保护/ruleset/CI gate：即使 agent 直 push 也被挡 | 硬 |
| 5 软引导 | AGENTS.md、identity 提示词、skill 正文 | 软 |

规则：声明中的 permissions（L1）是权限引擎（L2 框架）的输入；冲突时硬控制优先。拒审记录进事件流 `tool_called.denied_by`，供治理审计。

## 后果

- 最佳实践流程落地 = skill（软引导）+ acceptance[ci]（硬验收）+ permissions（硬边界）三者配套。
- 软控制失效不再等于失控：最坏情况被硬层截断。
