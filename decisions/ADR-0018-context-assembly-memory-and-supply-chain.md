# ADR-0018: 上下文装配清单、记忆契约与开源项目清单

- status: accepted
- date: 2026-08-19

## 背景

治理体系存在两个声明空白（走查确认）：

1. **启动上下文无声明**。simulate-wave 测相位/权限/预算，gate 测产品代码，
   没有任何一层管"agent 启动时实际拿到了什么"。装配内容散落在 prompt_ref、卡、
   knowledge_retrieval、applies_adr[] 各处，无统一装配清单——实现层各自决定，
   声明层管不住，产生不经意漂移。
2. **记忆声明是指导性的**。profiles 的 `typical.memory` 仅为指导；权限词表管了
   memory_read/write，但内容、寿命、销毁时交出什么都不在校验范围。由此产生
   ADR-0004 的断点：handoff 要求 stewardship 侧 `memory-distill`，但 agent 全部
   实例私有隔离、原始轨迹 30 天滚动清理——curator 蒸馏时素材无着落。

同时，`implementation.repo` 为自由文本且无人校验，`openJiuwen` 与
`openJiuwen-ai` 两个 org 名已并存于 3 个工具声明（本 ADR 附带修复）——
dep 类供应链防线（sca/license-check/hash-pin）管产品仓依赖，却不管
agent 体系自己引入的开源项目。

## 决策

1. **上下文装配清单**（[standards/context-assembly.yaml](../standards/context-assembly.yaml)）：
   组件词表（7 种，fail-closed）+ 每 LLM 原型一份有序 spawn manifest。
   清单外内容不得注入启动上下文（"多给了"与"少给了"同为违规）；
   每组件装配记 version_read。机制原型无 spawn 上下文，不设装配。
2. **记忆契约**（同文件 PART 3）：类型词表（semantic/episodic）+ 每原型
   types/retention；`memory_view` 组件 ⟺ types 非空（validate 强制双向一致，
   judge types=[] 由此从注释升为可校验事实）。记忆不是规范来源；实例私有，
   跨生命周期靠制品不靠记忆。
3. **memory_digest 制品**：ephemeral 团队 handoff 相位导出蒸馏素材落数据层
   （schema：registry/schemas/memory-digest.json），先于 workspace 销毁，
   不随 30d 轨迹清理（ADR-0003 的 curated 例外）；ephemeral 团队 handoff
   必含 `memory-export`（validate 强制）。curator memory-distill 的素材面
   唯一化——素材不可能先于消费者消失。
4. **开源项目清单**（[registry/projects.yaml](../registry/projects.yaml)）：
   tool `implementation.repo` 与 models.yaml `upstream_runtime.repo` 必须
   ∈ 清单（fail-closed）；条目必填 role/license/pin_policy/audit；
   反向无消费者=死条目拒绝。持续审计由 `check:supply-audit` 承担
   （CI-Workflows 定时 osv-scanner/renovate——Dependabot 只认包管理器
   manifest 不认 YAML 清单，故用扫描 job）；发现走 maintain_loop，
   不建平行流程。

## 测试收口（不新增门禁类型）

防线全部挂到既有两个门禁，每个新声明不建自己的小流程：

| 防线 | 载体 |
|---|---|
| 装配覆盖/组件词表/记忆契约一致性/digest schema 实存 | validate.py（结构校验） |
| 供应链引用收敛/死条目/审计字段完备 | validate.py（结构校验） |
| ephemeral handoff 含 memory-export | validate.py（结构校验） |
| S18/S19/S20 流程彩排 | scenarios.yaml 纯声明式 asserts（simulate-wave 求值） |
| 编排层注入收敛 | check:spawn-manifest-conformance（template_service 消费，checks.yaml consumed_externally） |
| 供应链持续审计 | check:supply-audit（CI-Workflows 消费，consumed_externally） |

跨仓协调经 checks.yaml 注册表（既有机制），本仓不越权改平台仓。

## 后果

- org 名漂移这类缺陷从此在 validate 层灭绝（本 PR 即抓到 read_file/write_file
  两处存量漂移并修复）。
- 启动上下文从"实现细节"升为"声明契约"；template_service 编排模板有了
  机器可对照的注入规范。
- 记忆生命周期闭环：spawn（memory_view 投影）→ 运行（私有）→ 销毁
  （memory_digest 过界）→ 蒸馏（curator）。
- license `unverified` 是诚实占位：supply-audit 首跑动作即补全并钉扎，
  不在注册层伪造审计事实。
