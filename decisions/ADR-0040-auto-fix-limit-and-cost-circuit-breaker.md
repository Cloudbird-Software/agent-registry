# ADR-0040: auto-fix 修复循环上限 + 额度/成本熔断（P2-8）

- status: accepted（2026-08-20）
- 背景: .github issue #81（自动合并计划）§6 工作卡 #93（P2-8）
- 关联: .github 仓 governance/policy/automation-limits.yaml（阈值真源）、governance/auto-fix-limit.sh、
  governance/cost-check.sh、.github/workflows/auto-fix-limit.yml、.github/workflows/cost-check.yml、
  .github/AGENTS.md（agent 行为契约）；ADR-0029（auto-merge 基线）、ADR-0034（liveness 侦测——
  本 ADR 是其对偶：liveness 管"卡死不烧钱"，本 ADR 管"在烧钱必须停"）

## 背景

一个坏循环能烧掉整月额度：agent 修红 → 失败 → 再修 → 再失败，无人值守下没有自然终止条件（#81 §6）。两条敞口：

1. **auto-fix 无上限**：PR 永修不好时循环没有终止条件——Actions 分钟与 LLM token 均无硬顶。
2. **成本无熔断**：用量逼近/超出预算无人知晓，没有任何机制在"正在被烧穿"时踩刹车。一人公司这是生存问题。

## 决策

1. **auto-fix 上限（N=3）**。修复尝试计数 = PR 各 commit 上 `gate` check run 的最新失败结论数
   （failure/timed_out/startup_failure/cancelled；非头 commit 上的未完成结论亦计——fail-closed 方向：
   多计早关优于少计烧额度）。计数真源 = Checks API（commit 元数据），非内存态——runner 崩溃/
   workflow 重启后计数天然续接而非清零（工作卡 T3 持久性由构造保证，无状态文件可丢）。
   扫描器（.github 仓 `governance/auto-fix-limit.sh`，小时级 cron）发现 agent（cloudbrid-agent[bot]）
   的 open PR 失败计数 ≥ N：撤 auto-merge → 关闭 PR → 打 `auto-fix-limit-exhausted` 标签 →
   在 .github 仓开说明 issue（含每次失败的 run 链接）。非 agent PR 打 `auto-fix-loop` 标签 opt-in 同路径。
   带 exhausted 标签被 reopen 的 PR 由下一轮扫描再次关闭（计数是历史事实，不因 reopen 归零）。
2. **成本熔断（Actions 分钟）**。`governance/cost-check.sh`（6h cron）经
   `GET /orgs/{org}/settings/billing/usage`（旧 `/settings/billing/actions` 端点 2025 迁移后 410）汇总当月
   Actions 分钟，对 `policy/automation-limits.yaml` 声明的月预算：≥80% 开告警 issue（同日去重，不硬停）；
   ≥100% 置 org Actions 变量 `AUTO_MERGE_DISABLED=true` + 撤全部 open PR 的 auto-merge + 开 P0 issue。
   全仓公开（ADR-0020）下 Actions 计费净额恒为 $0——预算是声明的"烧穿速率"护栏而非账单上限，防的是
   失控循环的时间黑洞；阈值 owner 可调，单一真源在 policy 文件。
3. **熔断标志消费点**（两处，缺一不可）：(a) 行为层——agent 派发入口与 automerge 启动前必须检查
   org 变量（.github/AGENTS.md 硬规则），置位即停一切派发与 auto-merge enable；(b) 机器执法——
   auto-fix-limit 扫描器每轮发现置位即撤所有 open PR 的 auto-merge，新 enable 的旁路窗口 ≤1h（扫描周期）。
4. **人工复位**：仅 owner（randypanding）。复位动作 = PATCH org 变量为 false（或 DELETE）+ 在 P0 issue
   留复位评论（留痕=issue 评论历史）；cost-check 观察到"变量已复位且用量 <100%"后自动关闭 P0 issue。
   置位仅由用量数据触发、复位仅人工——脚本不做自动复位，否则熔断失去意义。
5. **fail-closed 边界**：API 读失败（用量/PR/check runs/变量）= 基础设施故障通道（exit 2 + 专属
   label issue + 运行变红），不直接置熔断——假熔断要求人工复位，会把整条流水线停摆（另一个方向的
   生存风险）。盲区由 agent 行为规则补：派发前须确认无未决 cost-infra / cost-circuit-breaker issue。
6. **LLM token 预算**：阈值先行声明于 policy（llm_tokens 段），数据源（llm-gateway usage 端点，
   ADR-0025 部署物）未就绪前标 `data_source: pending`——仅声明+注入通道，不触发真实告警；
   数据源落地后与 Actions 分钟同路径接入（同一 tier 判定/同一熔断变量）。
7. **注入测试通道**：全部阈值/用量/作用域可经环境变量覆盖（workflow_dispatch inputs 透传），
   T1（构造必红 PR）/T2（79%/85%/100% 注入）/T3（计数续接）均不需要真实超支或真实烧额度。

## 后果

- 永修不好的 PR 在第 N 次失败后 ≤1h（扫描周期）被自动关闭并留 issue，不再重试；计数跨崩溃持续。
- 熔断置位后：既有 auto-merge 即轮撤销、新 enable 旁路窗口 ≤1h、agent 派发行为层停止；复位仅人工。
- 计数/用量全部从 API 事实派生——无状态文件、无内存态；篡改标签只损失可见性不损失计数。
- 扫描为小时级只读 + 少量写操作（超限时），API 调用预算在现有 drift-check 限流余量内。
- 熔断变量是运行态标志，刻意不纳入 expected-state.json（置位/复位是运行动作而非期望状态，纳入会造成
  复位后 drift-check 反向"修复"回去的对账冲突）。
