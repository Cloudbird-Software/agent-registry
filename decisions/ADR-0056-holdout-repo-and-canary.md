# ADR-0056: holdout 仓与泄漏诱饵（试卷层实体化）

- status: accepted（2026-08-21）
- 背景: IR-0003（.github#161）W1 工作卡 .github#167；宪法 §1（试卷层）、§4B（判定物
  有效性——泄漏诱饵）、§6（holdout 泄漏诱饵报警）、§2（owner 月度 30min 补给职责）、
  §11（cron 每周行：holdout 诱饵检查）；IR-0001 DECISION-02（holdout 公开仓 + App
  安装差异隔离）、IFACE-07（holdout 条目 schema）
- 关联: ADR-0021（REPOS.yaml 申报/直推豁免机制）、ADR-0034（drift-check 分节编号体系）、
  ADR-0047（治理标签）、宪法 §13 推论一（agent-trajectory 第四观测类）

## 背景

宪法 §1 定义了试卷层（holdout = 封存验收场景 + golden 集 + 泄漏诱饵，owner 直管），
但该层尚无实体仓。IFACE-07 已定义条目 schema 骨架，但无落盘 schema 文件、无校验器、
无封存/引用约定。宪法 §4B/§6 要求"holdout 内容出现在任何 agent 上下文/日志即报警"，
该不变量需要检测机制（诱饵注册 + 周期扫描 + 演习正控），否则只是一句愿望。

隔离设计沿 IR-0001 DECISION-02：holdout 是公开仓（agent 读公开仓是不确定风险，
私有化的运维是确定支出），隔离靠 **cloudbrid-agent App 不安装到该仓**——agent 的
读隔离不靠保密（公开仓无密可保），而靠"违规读取可检测"（诱饵 marker 出现在
workflow 日志 = 违规证据）。

## 决策

1. **建仓 `Cloudbird-Software/holdout`**：public，L1，owner 直管（REPOS.yaml 申报
   role: 试卷层）。**cloudbrid-agent App 严禁挂载**（DECISION-02 隔离不变量）——
   new-repo-init.sh 的 App 挂载步骤对 holdout 禁止执行，只做仓库基线（squash-only/
   删分支/auto-merge/关 wiki+projects）+ production environment 的等价设置。
2. **drift-check 新增 §18（holdout 隔离断言）**：用 GOVERNANCE_TOKEN 列出
   cloudbrid-agent installation 的全部仓，断言 holdout 不在清单（在 = P0 漂移）；
   正向对照防检测器失明：断言清单非空且含 `.github`（连 .github 都不在 = 端点读法
   错了/权限变了，fail-closed 报漂移）；API 失败一律 fail-closed。§17 编号预留给
   并行卡 W1-C3，本卡用 §18。
3. **条目 schema（IFACE-07 落盘）**：`schema/entry.schema.json`——`id` ^HO-\d{4}$、
   `ir_ref|ac_ref` 二选一（oneOf）、`type` ∈ {e2e-scenario, golden, agent-trajectory,
   canary}（agent-trajectory 源自宪法 §13 推论一）、`payload` object、`sealed_sha256`
   ^[a-f0-9]{64}$、`created_at` date-time、`sealed_by` string。索引文件自身有
   `schema/index.schema.json`。条目文件统一为纯 JSON（entries/HO-NNNN.json）。
4. **封存/引用约定**：`sealed_sha256` = sha256(canonical JSON of payload，
   `json.dumps(payload, sort_keys=True, separators=(",", ":"))`)；**spec/PR/卡只能
   引用 `id` + `sealed_sha256` 前 8 位，禁止引用 payload 内容**（引用内容 = 提前
   泄题 + 破坏封存可验证性）。揭封 gate 属 W4-C3，本 ADR 只立约定不建揭封流程。
5. **泄漏诱饵（canary）**：type=canary 的条目 payload 内嵌唯一 marker
   `CLOUDBIRD-HOLDOUT-CANARY-<16hex>`（openssl rand -hex 8）；`canary/registry.yaml`
   登记全部 marker + drill 标志。**registry 含且必含 ≥1 条 drill: true 演习 marker**
   ——正控必须在场：sweep 全部未命中且无 drill 命中 = 检测通道可能坏了，报 P1
   （fail-closed 思想，宪法 §6 缺席触发）。markers 公开是设计而非缺陷：仓本就
   公开，告警语义 = marker 出现在 agent 上下文/workflow 日志 = 违规读取，而非
   marker 保密。
6. **canary sweep（检测机制）**：`.github` 仓新 workflow `holdout-canary-sweep.yml`
   ——weekly cron（错峰）+ workflow_dispatch（inputs: `treat_drill_as_leak` 默认
   false、`since_days` 默认 7）。对 REPOS.yaml 全部 active 仓的近窗口 workflow run
   日志逐仓 grep 全部 marker（每仓上限 50 run，超限报 P1 注记）。命中非 drill
   marker → 开 P0 issue（label holdout-leak，幂等：已有 open 同 label 不重复开）
   + run 变红；命中 drill marker → `treat_drill_as_leak=false` 时报"演习正控命中 ✓
   检测通道健康"（run 绿），`=true` 时同样开 P0（AC-3 演习路径：证明报警真的
   会触发）。输出 AUDIT 行（trigger/扫描仓数/run 数/命中明细/registry 拉取 sha）。
7. **canary drill（演习）**：`.github` 仓新 workflow `holdout-canary-drill.yml`
   （仅 workflow_dispatch）——echo 一条已注册 drill marker 到本 run 日志（模拟
   "holdout 内容泄漏进日志"）。演习序列：drill run 产生日志 → sweep
   dispatch(treat_drill_as_leak=true) → 断言 P0 issue 开出 → 手动关闭留评论"演习"。
   每月 owner 补给 holdout 时至少演习一次（与 §2 月度职责合并执行）。
8. **校验器**：`scripts/validate_entries.py`（schema 合规、id 唯一递增、
   sealed_sha256 == canonical JSON 哈希、canary registry ↔ entries 双向一致）+
   `scripts/new_entry.py`（生成新条目、算哈希、防 id 冲突）。CI（PR+push+weekly
   cron）跑 validate，python 3.12，action SHA 钉版。
9. **owner 月度补给职责（宪法 §2/§7）**：30 分钟/月——新增条目（e2e/golden/
   trajectory 各至少 1）、轮换一条 canary marker、执行一次 drill 演习。结构上
   不可交给 agent（agent 补给 holdout = 运动员写考卷）。

## 后果

- 正面：宪法试卷层有了实体 + 机器可判定的封存完整性（哈希锚定）+ 泄漏检测闭环
  （诱饵注册→周期扫描→演习正控→报警通道），DECISION-02 隔离不变量进入小时级
  drift-check 执法（§18）。
- 负面/代价：sweep 每周扫全部 active 仓日志（API 配额消耗，每仓 50 run 上限封顶）；
  marker 公开意味着攻击者可主动避免输出 marker——本机制防的是**无意的**违规读取
  （agent 好奇心/工具链缓存），不是对抗性外泄（后者由 App 不挂载 + 私有 payload
  揭封 token 兜底，DECISION-02）。
- 风险与缓解：sweep 误报（marker 子串碰撞——16hex 熵 64bit，碰撞概率可忽略）；
  正控缺失误报（新仓无 workflow 日志时 drill marker 必然未命中——所以 drill
  marker 由 sweep 自身 dispatch 的 drill run 日志承载，drill: true 命中即证明扫描
  通道端到端可用）。
- 回滚：删除 holdout 仓 + .github 仓两个 workflow + drift-check §18 + REPOS.yaml
  条目，一次 PR 可逆（DECISION-02 可逆性声明延续）。
