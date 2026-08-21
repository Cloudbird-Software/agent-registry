# ADR-0055: 统一入口协议块 + factory-floor 只读投影板 + dashboard 账本

- status: accepted（2026-08-21）
- deciders: 人（owner randypanding）+ AI
- 关联: 宪法 §11（统一入口/唤醒矩阵事件行）、§12（状态可视化）、§4D（AGENTS.md 索引型+协议块统一下发）；
  工作卡 [.github#166](https://github.com/Cloudbird-Software/.github/issues/166)（父意图 #161）；
  前置：ADR-0051（找活协议）、ADR-0049（conductor）、ADR-0054（arbiter 内核）、ADR-0057（管家骨架/butler-ledger）。

## 背景

外部 agent 进组织工作此前需要人类补提示词；宪法 §11 要求入口=各仓 AGENTS.md 的同一协议块
（template-service 统一下发，drift-check 校验一致），且写入类命令（/claim 等）经 arbiter
裁决（唤醒矩阵事件行："仲裁请求处理（/claim 等，转 arbiter）"）。W1-C2 已交付 arbiter 内核
（CAS 租约/防重放/默认拒绝，ADR-0054），但 conductor 尚未转介；§12 要求的两个投影
（org Project 板 factory-floor、dashboard 账本 issue）尚不存在。本 ADR 把三者一次接通。

## 决策

1. **协议块（canonical，v1）**：以 HTML 注释为块边界——`<!-- entry-protocol v1 -->` …
   `<!-- /entry-protocol -->`，内容自包含（≤10 行）：三命令找活协议
   `ghcb next` → `ghcb claim <n>`（conductor 转介 arbiter 原子 CAS，先到先得）→
   `make card-test CARD=<n>` / `make gates-pr`；front-desk 命令集 /claim /release /retry
   （issue 评论，conductor/arbiter 处理）；提 PR 规矩=body 必带一行卡元数据
   `Card: <owner>/<repo>#<n>`（缺失=后续关卡 exit 3，本卡只立约定、关卡执法随后续卡）；
   ghcb 取用 URL=钉 commit SHA 的 raw 链接（模式同 template-service AGENTS.md 现有
   gh-app-token.sh 钉法，ADR-0021：禁浮动 main 指针，升级先比对 .github main 再换 SHA）。
2. **版本纪律**：协议块以标记中的版本号（v1）演进；任何内容变更须 bump 版本并在
   template-service 与 .github 两仓的 AGENTS.md **同步**落地（同一 PR 窗口内先后合并），
   drift-check §17（决策 7）在中间态报警是预期行为（合并窗口 <1h）。产品仓 rollout
   （给 7 个业务仓下发协议块）是后续 fleet 小卡，不在本 ADR 范围。
3. **template-service AGENTS.md 重写**为 ≤30 行（宪法 §4D CG-1）且包含协议块——
   精简现有硬规则/索引腾空间；Makefile 新增 `card-test`（CARD=N：拉卡 AC 列表+提示
   测试先行）与 `gates-pr`（本地等价检查清单，引导 gate.yml 语义）两目标。本地无 CI
   镜像，两目标是诚实薄封装，不伪装已运行 CI。
4. **.github AGENTS.md 治理仓豁免至 ≤40 行**（CG-1 为 ≤30）：该仓是卡实际所在仓
   （AC-1 e2e 的入口），须同时容纳协议块（9 行）+治理硬规则+索引三合一；超出部分
   仅此 10 行预算，且协议块本体仍受 §17 逐字节校验约束。
5. **ghcb 扩展**（.github/scripts/ghcb，现有 next/claim 语义不动）：新增
   `ghcb release <n> [repo]`（评论 /release——释放 arbiter 租约）、
   `ghcb status <n> [repo]`（只读：issue 标签态+经 arbiter 仓 `refs/leases/<org>__<repo>__<n>`
   API 读租约持有者/到期，无任何写操作）、`ghcb card-meta <n>`（输出 PR body 应贴的
   `Card: <owner>/<repo>#<n>` 元数据行文本）。
6. **conductor 转介 arbiter**（conductor.yml，ADR-0049 路由层叠加授权）：
   - 铸第二个 App 安装令牌 REPO=arbiter（App 已装 arbiter，installation#154584760；
     AG-1 单仓最小作用域同现有 .github 令牌）；
   - checkout arbiter main（受信源：conductor 只在 main 上下文运行事件路由，
     与 checkout 本仓 transitions.yaml 同级信任）；
   - 对 `comment:/claim`（T3）与 `comment:/release`（纯租约面，transitions.yaml 未列
     该事件、不产生标签转移）前置调用 `bash arbiter/scripts/adjudicate.sh <cmd>
     --card Cloudbird-Software/<repo>#<n> --sender <actor> --sender-role <role>
     --delivery-id <comment node_id> --event created --current-state <当前态>
     --backend github`（参数以 arbiter 仓 cli.py 为准，ADR-0054）；
   - 退出码三态：**0=allow/noop** → 继续原有 T3 动作（swap 标签+assignee；/release
     则仅审计）；**1=deny** → AUDIT 行 `verdict=DENIED-by-arbiter` + no-op
     （对齐现有 silent-drop：无标签变更、无评论）；**2=infra** → AUDIT + run 红灯
     fail-closed——**不许绕过仲裁**（仲裁器失明≠放行）。
   - guard 先于转介（本地廉价检查先行，避免为注定拒绝的请求创建租约）；/retry（T4，
     quarantine 回流）的转介**本卡不做**——arbiter /retry 语义=require_holder，
     直接接入会收紧 owner 驱动的回流路径，留待 quarantine 流程卡定夺。
   - 附带收紧（有意）：T3 guard 原允许 MEMBER 协作身份认领，转介后 arbiter 策略表
     只认 agent/owner 角色（capabilities.yaml，ADR-0054）——分层授权取更严者，
     deny 优先。org 人类 owner 与 App bot 均不受影响。
   - **双层防线**：两次 /claim 同卡并发时，conductor 的 per-issue concurrency 串行化
     使第二个 run 排队，届时当前态已 in-progress → from_state 不匹配=no-op（ADR-0049
     幂等）；即便事件乱序到达，arbiter CAS（createRef 422=lost-race）也兜底恰一胜者。
   - **transitions.yaml 不改**：仲裁是叠加授权层，状态机转移定义唯一真源不变。
7. **board-sync**（.github/governance/board-sync.py，纯 stdlib）：GraphQL
   （GOVERNANCE_TOKEN——GITHUB_TOKEN 无 org project 权限；cloudbrid-agent App 亦无：
   其安装权限仅 issues/contents/pull_requests，无 organization_projects/members，
   org admin PAT 是唯一可用身份。**AG-1 例外在此记录**——org 级 Project(v2) 写与
   conductor 组织成员判定用 GOVERNANCE_TOKEN，仅存在于 workflow secrets 面，不落
   agent 手；升级路径=给 App 增设 organization_projects 权限后收回本例外）
   幂等确保 org Project(v2)
   「factory-floor」存在；字段=State（单选，选项=state 全集，颜色取自
   expected-state.json#labels）、Repo、Assignee、卡号、停留天数（updated_at 距今天数）、
   AC 进度（v1 从 issue body checkbox 解析，解析不了留空）。**单向投影 label→board**：
   对 REPOS.yaml 全部 active 仓的 open+state:* 卡同步字段；覆盖前比对，board≠label →
   输出 `WARN board-drift <card>: board=X label=Y（人工改动将被纠正，宪法 §12）`+计数
   后照 label 纠正；已 done/closed 的条目 v1 状态字段照实设、不删条目。每 run 输出
   AUDIT 行（sync 数/纠正数/报警数）；API 失败 exit 2（fail-closed）。
8. **dashboard 账本**（.github/governance/dashboard-update.py）：幂等找到/创建 issue
   `管家账本 dashboard（factory-floor）`（label `dashboard` 幂等创建）；body 两区=
   `<!-- dashboard-json -->` 后置 fenced json 机器可读区（generated_at、cards[]、
   sli{automerge_rate,human_touch_per_pr,escape_rate,stuck_prs,false_red_rate,
   entropy_delta}——字段名与 #98 SLI 口径对齐；v1 能算的算：automerge_rate=近 7 天
   merged PR 中 App 身份合并占比（merged_by=cloudbrid-agent[bot]，方法注记在块内）、
   stuck_prs=open PR 超 24h 数；算不了的置 null + sli_pending 标 `"W5-C3"`）+
   人类一屏摘要区（数字+链接）。更新=issue edit 覆盖 body，历史靠 issue 编辑历史留痕。
9. **drift-check §17（协议块一致性）**：REPOS.yaml 新增 `entry_protocol: true` 字段
   （本卡只标 template-service 与 .github）；对带该字段的仓 fetch 其 main 的
   AGENTS.md raw，提取协议块（标记间内容）与 template-service main 的块**逐字节**比对；
   缺失标记/不一致/fetch 失败=DRIFT（fail-closed）。插入位置=§16 与 §18 之间。
10. **但书（b-room 双写防竞态）**：butler-ledger.yml（ADR-0057，已合并）已在 */15 cron
    守卫调用本卡两脚本；故本卡新增 board-sync.yml **只有 workflow_dispatch、无 cron**
    （手动/演习通道），且 concurrency 组与 butler-ledger 同名（`butler-ledger`）——
    GitHub concurrency 组按仓全局生效，手动面与 cron 面互斥串行，杜绝同一投影双写。
    日常驱动权单一归 butler-ledger（唤醒矩阵行 2），board-sync.yml 头注释写明职责划分。
11. **.github 新增薄 Makefile**（card-test/gates-pr 两目标，与 template-service 同构）：
    治理仓是入口协议的 e2e 现场，其自身必须兑现协议块第 4 步承诺；本地等价清单
    （bash -n/yaml 解析）真实执行，CI 关卡语义仍以 gate.yml 为准。

## 后果

- 正面：陌生 agent 仅读任一携带协议块的 AGENTS.md 即可完成找活→认领→开工→合规 PR
  全链路（宪法 §11 入口判据 / spec AC-2 复测=本卡 AC-1）；写入类命令获得仲裁层
  双保险（label 状态机 + CAS 租约）；状态可视化两投影落地，label 唯一真相源可机器复核。
- 负面/代价：conductor 每次 /claim、/release 多一次 arbiter checkout+仲裁调用
  （~10-15s，事件驱动低频可接受）；MEMBER 身份认领被 arbiter 收紧（决策 6 附带）；
  drift §17 新增 N 次 raw fetch（N=entry_protocol 仓数，v1=2）；协议块变更需两仓同步
  PR（合并窗口内 §17 短暂报警——预期中间态）。
- 风险与缓解：ghcb 钉 SHA 过期（新命令不在钉点）→ 版本纪律同 ADR-0021：升级走 PR
  换 SHA；Project GraphQL schema 变更 → fail-closed exit 2，butler-ledger 审计行
  infra-fail 报警，不影响 label 真相源；dashboard issue 被人手改 → 每 15min 覆盖式
  刷新天然纠正（编辑历史留痕可审计）。
- 回滚：整链新增式。停 conductor 转介（revert conductor.yml 增量）即回到 W0 行为，
  arbiter 租约 ref 自然过期（TTL 240min）；board-sync/dashboard-update 从 butler-ledger
  守卫中自动失效（文件移除即 skipped）；协议块删除 + REPOS.yaml 摘 entry_protocol
  字段即完整退场；无数据迁移、无状态残留（issue label 全程未动）。

## 验证

- 本卡 AC-1 e2e（.github#166）：干净环境陌生 agent 仅读 AGENTS.md → ghcb next/claim →
  arbiter 租约 + conductor 置态 → 带 `Card:` 元数据 PR → /release 清理。
- AC-2：drift-check §17 对两仓协议块逐字节一致；人为改块 → DRIFT。
- AC-3：board-sync 手改 board 后下一轮 WARN board-drift 并纠正回 label。
- AC-4：dashboard issue 含 `<!-- dashboard-json -->` json 块+一屏摘要。
