# ADR-0057: 管家骨架——唤醒矩阵前三行 + 审计日志 + dead-man 心跳 fail-closed

- status: accepted（2026-08-21）
- deciders: 人（owner randypanding）+ AI
- 关联: 宪法 §2（管家六职）/§6（缺席即停）/§11（唤醒矩阵）/§12（投影二 dashboard 账本）；
  .github issue #168（W1-C5）；SLI 口径参考 #98；预算检查演进自 ADR-0040（cost-check）

## 背景

宪法 §11 立铁律：**管家永远不"自己醒来"**——每次运行必须有明确触发器，且每次运行
产出审计日志条目（谁唤醒/干了什么/花了多少），否则即为设计错误（INV-12）。W1 波次
（IR-0003 #161）的 W1-C5 卡负责把唤醒矩阵**前三行**从宪法文本落成可运行的 workflow：

| 触发器 | 职责 | 本卡落地形态 |
|---|---|---|
| cron 每 6h | reconcile（僵尸卡/孤儿标签/隔离超时） | `butler-reconcile.yml`（17 */6 * * *） |
| cron 每 15min | 账本/dashboard 刷新 + Project 板同步 | `butler-ledger.yml`（*/15 * * * *） |
| cron 每 1h | 预算/配额检查 | `cost-check.yml` cron 由 6h 收紧至 1h |

外加 §6 的两条 fail-closed 基础设施：外部 dead-man 心跳的 **ping 侧**
（`butler-heartbeat.yml`）与 **trip 侧**（`butler-deadman-trip.yml`，缺席即停自动合并），
以及统一审计形态 `governance/butler-audit.sh` 与策略真源 `governance/policy/butler.yaml`。

矩阵第四行起（每日 digest/flaky sweep、每周审计包/种子缺陷演习）属后续波次，
**不在本 ADR 范围**，也不在 butler.yaml 中占位声明（未落地的职责不预先声明，防"声明了
但没有触发器"的宪法违规）。

## 决策

1. **唤醒矩阵前三行声明进 `governance/policy/butler.yaml`**（机器可读：脚本读它，
   不读注释）。每行声明 trigger/cadence/职责/对应 workflow 文件；阈值同放此文件
   （stale_in_progress_days: 3 / stale_quarantine_days: 2 / deadman_grace_minutes: 60）。
   阈值改动走 C1（本文件在 governance/ 路径下，PR 必须引用本 ADR）。
2. **INV-12 审计形态 = 运行日志 + step summary，不 commit main**。每个管家 workflow
   在每个动作前输出统一审计行（`governance/butler-audit.sh` 生成）：
   `AUDIT | butler=<名> | trigger=<触发器> | run_id | repo | started | duration_s |
   outcome | actions=<JSON>`，并 append 到 $GITHUB_STEP_SUMMARY（owner 免翻日志）。
   刻意不把审计条目 commit 回 main——管家 commit main 会制造 §8（直推漂移）执法面
   上的噪音，运行日志（GitHub Actions run logs）已是带 run_id 的不可变第三方台账。
   审计 actions JSON 为 SLI 字段（#98 口径：auto_merge_rate / check_latency /
   revert_count 等）预留键位——账本 JSON 状态块由 W1-C3 的 dashboard 脚本负责，
   本卡只保证审计条目结构兼容。
3. **reconcile（6h）**：遍历 REPOS.yaml active 仓，三类检查——
   (a) state:in-progress 卡 updated 距今超 stale 阈值 → 开/评论 needs-human issue；
   (b) closed issue 仍挂 state:* 标签（孤儿标签）→ 记入 reconcile 报告 issue；
   (c) state:quarantine 停留超阈值 → 升 needs-human。
   v1 只开 issue 不改标签（写状态标签的动作留给 conductor/仲裁路径，INV-02）；
   needs-human/报告 issue 用 GITHUB_TOKEN 开在 .github 仓（issue 写操作最小权限，
   无跨仓写需求）。幂等：报告 issue 用固定 label `butler:reconcile` 去重；
   同卡 needs-human 去重（open issue 标题含卡号即评论不重开）；同日全绿不评论（防灌水）。
   GOVERNANCE_TOKEN（跨仓读）缺失 → fail-closed 变红 + 审计行，不静默降级。
4. **账本刷新（15min）**：`butler-ledger.yml` 调用 W1-C3 的
   `governance/board-sync.py` / `governance/dashboard-update.py`。两脚本本卡时点
   **尚不存在**（C3 并行开发）——workflow 用 `[ -f ... ]` 守卫：存在才跑；不存在输出
   `skipped: dashboard-scripts-not-landed(W1-C3)` 审计行且**保持绿**。守卫原因：
   账本刷新骨架先行（cron 节奏与审计形态先定型），投影脚本随后接入即自动生效，
   避免两卡相互阻塞。骨架期本卡自带轻量记账：每次运行追加 dashboard 备注行
   （v1 仅审计日志，不动 issue）。
5. **预算检查 cron 6h→1h**（宪法 §11 第三行）：`cost-check.yml` cron 改
   `23 * * * *`（每小时 :23，避开整点 governance-drift 与 :18 auto-fix-limit）。
   判定逻辑零改动，仅头尾加审计行（trigger/duration）。熔断继续用
   org 变量 `AUTO_MERGE_DISABLED`（ADR-0040）——dead-man trip 与 cost-check
   **共用同一熔断变量**：宪法 §6 的"缺席即停"与成本熔断都是"停自动合并"语义，
   两个变量会造成两套复位路径、两套旁路窗口。
6. **dead-man 心跳双侧设计（§6）**：
   - **ping 侧**（`butler-heartbeat.yml`，*/30）：org secret `DEADMAN_PING_URL`
     已配置 → curl 外部 dead-man 服务（healthchecks.io 或任意同类）；失败重试 1 次
     后变红 = 心跳管道自身故障可见。未配置 → WARN 审计行不红（外部服务注册是
     owner 手工步骤，见 `docs/deadman-setup.md` runbook；骨架期不因缺配置阻塞 CI）。
   - **trip 侧**（`butler-deadman-trip.yml`）：`repository_dispatch(deadman-tripped)`
     （外部服务超时回调触发）+ workflow_dispatch（演习）。动作：置
     `AUTO_MERGE_DISABLED=true` + 撤全部 active 仓 open PR 的 auto-merge（复用
     cost-check.sh 的 strip_all_automerge 模式）+ P0 issue（label `deadman-tripped`，
     幂等去重）。"心跳是唤醒的唤醒，也必须外部"——GitHub 侧只做被动的 ping 客户端
     与 trip 接收方，缺席判定在外部服务（GitHub cron 全挂时 GitHub 自己无法自我报警）。
   - **fail-closed 实证路径**：心跳暂停 → 外部服务 grace（= butler.yaml
     deadman_grace_minutes）超时 → 回调 repository_dispatch → 熔断。AC-3 演习 =
     手动 dispatch trip。
7. **回滚 = 删 workflow**。全部新增式：删 4 个新 workflow + 还原 cost-check.yml cron
   即回到 W1 前状态；butler.yaml/butler-audit.sh/deadman-setup.md 无运行时副作用，
   可留可删。无 schema/状态迁移，无数据回填。

## 后果

- 正面：宪法 §11 前三行与 §6 缺席即停从文本变为可运行、可审计、可演习的基础设施；
  所有管家动作有统一审计行（INV-12 机器可查）；dashboard 脚本守卫使 C3/C5 两卡
  解耦并行。
- 负面/代价：新增 4 个 cron workflow 的 Actions 分钟消耗（公开仓免费额度内，量级：
  15min 账本刷新 ≈ 96 run/天 × <1min）；心跳每 30min 一次外呼。dead-man 外部服务
  的注册/配置是 owner 手工步骤（runbook 已写明），未配置期间 trip 通道处于
  "可演习、未实连"状态——诚实接受，不假装已闭环。
- 风险与缓解：reconcile 误报（活跃卡被判 stale）→ stale 阈值 3 天保守 + 只开
  needs-human 不自动改状态 + dispatch 注入通道（stale_days_override=0）支持演习；
  心跳 workflow 自身挂掉 = 与管家 cron 同死 → 这正是外部 dead-man 存在的理由
  （外部服务监督包括 heartbeat 在内的全部 cron 的静默）。
