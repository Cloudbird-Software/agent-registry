# ADR-0054: arbiter 仲裁内核 v1——独立仓、纯 CAS 租约、无 LLM、默认拒绝

- status: accepted（2026-08-21）
- 背景: IR-0003（重订宪法）W1-C2 工作卡 .github#165
- 关联: 宪法 §1（结构分层：仲裁内核=独立最小仓）、§6（失效与降级 fail-closed）、
  §11（唤醒矩阵：issues.labeled / issue_comment.created → 仲裁请求处理，
  转 arbiter）、ADR-0049（conductor 骨架——arbiter 与其分立）、ADR-0051
  （ghcb claim 认领协议——arbiter 为其原子层）

## 背景

W0 的 /claim 认领由 conductor guard + issue label swap 实现：无原子性
（两个并发 /claim 都可能通过 guard 再竞写 label），无租约（认领者跑路后
卡无超时回收），无防重放台账（delivery 幂等靠 from_state 巧合）。宪法 §1
因此设独立仲裁内核仓 `arbiter`：**写入仲裁（认领/释放/重试）的裁决必须
是确定性纯函数 + 原子提交**，且不能由被审计的一方（管家/conductor）自审。

## 决策

1. **独立仓，不进 conductor/管家**（宪法 §1 拆家原则）：被审计者不得组装
   审计报告——若 arbiter 是 conductor 的子模块，管家既做编排又做裁决，
   周审计时"裁决日志"与"编排日志"同源，失去独立复核面。arbiter 是 L2
   最小仓，只含：策略表（capabilities.yaml）、裁决内核（纯函数）、
   CAS 后端（GitHub refs）、租约模型、测试与误放行台账。
2. **CAS 选型 = git refs createRef 原子性**：租约与防重放标记都用
   "创建一个此前不存在的 ref"表达——GitHub API 对已存在 ref 的 create
   返回 422，天然 compare-and-set，无需读-改-写、无竞窗口。
   - 租约 ref：`refs/leases/<owner>__<repo>__<n>`，指向的 commit 内嵌
     JSON `{card, holder, acquired_at, ttl_minutes}`；
   - 防重放标记 ref：`refs/seen/<delivery-id 的 sha1>`，422 = 已处理
     → 幂等 no-op（AC-3）；
   - 每卡至多 1 个活跃租约 = 每卡恰一个 ref 名，结构性保证，不是检查。
3. **无 LLM 边界（INV：授权决策零 LLM）**：arbiter 全仓纯 Python 3 标准
   库 + bash，零第三方依赖（含 PyYAML——策略表用受限子集解析器加载）；
   CI 静态扫描断言：(a) kernel/policy/lease 模块不 import 任何网络模块；
   (b) backend.py 的 URL 常量 ⊆ {api.github.com}；(c) 全部源码不含
   LLM 端点/SDK 特征串。
4. **默认拒绝 + fail-closed 双通道**：capabilities.yaml 无匹配规则 = deny
   （不是 abstain，不是 error）；策略表加载严格校验（未知键拒绝启动）。
   退出码三分：0=allow / 1=deny / 2=infra——API 失败既不是拒绝也不是
   放行，走独立 infra 通道（宪法 §6 缺席即停的精神：拿不到证据就不裁决）。
5. **裁决纯函数化**：kernel.adjudicate() 不读 GitHub issue（状态由调用方
   conductor 转介时以 `--current-state` 传入）、不持时钟（`--now` 可注入）、
   不 import 网络模块——同输入必同输出，测试可全离线重放。
6. **防重放**：只认 `--event created`（edited 直接 deny，纵深防御）；
   同 delivery-id 二次投递 = seen ref 已存在 → no-op + 台账可查。
7. **误放行/误拒台账**（宪法 §8 安全正确性指标的落盘形态）：
   `tests/false_decision_ledger.jsonl` 记录重放比对中发现的误放行/误拒，
   记账约定见仓内 docs/FALSE-DECISIONS.md——每条须含输入、期望、实际、
   根因，回流路径=修复+回归测试。
8. **命令集 v1**：/claim（state=ready 且 sender_role∈{agent,owner}，
   CAS createRef，422=败者明确 lost-race 回复）；/release、/retry
   （校验 holder 本人或 owner 且租约未过期后删 ref；过期或 holder 不符
   → deny 而非静默删——AC-4）。TTL 默认 240 分钟，唯一来源
   capabilities.yaml。
9. **回滚 = 整仓可拆**：arbiter 是新增式设施（宪法 §6），回滚即删仓/
   停转介——conductor 退回 W0 label-swap 行为，无数据迁移、无反向依赖。

## 后果

- 正面：认领原子性从"guard 巧合"升级为结构性 CAS；裁决可独立离线重放；
  审计面与编排面分离（§7 owner 独立复算的前提）。
- 负面：GitHub refs 成为租约存储，refs 数量随卡片增长（每卡≤1 租约+每
  delivery 1 seen 标记，量级=事件量，可接受；seen ref 的清扫留待 v2）。
- 风险与缓解：refs API 失败≠拒绝≠放行（infra 通道，exit 2，调用方重试）；
  策略表漂移由 CI policy-validate 守住（加载失败=CI 红=fail-closed）。
