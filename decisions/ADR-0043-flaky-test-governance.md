# ADR-0043: flaky 测试治理——重试入账、识别、带过期隔离（P2-9）

- status: accepted（2026-08-20）
- 背景: .github issue #81（自动合并计划）§6 工作卡 #94（P2-9）
- 关联: CI-Workflows check.yml（重试接线）、governance/policy/testing.yaml#flaky_governance、
  ADR-0035（test-integrity——隔离清单变更共用 ADR 逃生门）、ADR-0032（EXPECTED_SKIP）

## 背景

假红的成本不是一次 rerun，而是"人被迫回到环路里"——无人值守下假红是最隐形的
人类瓶颈。同时"无声重试到绿"是另一种作弊：真回归会被当成 flaky 刷掉。设计
约束（#94）：重试次数入账且封顶；隔离必须带过期时间，过期自动回炉；隔离清单
变更必须走 ADR（防 agent 把真回归塞进隔离清单）。

## 决策

1. **自动重试与入账**：测试失败自动重试 ≤ `retry_max`（默认 2，即总运行
   ≤3 次）；每次重试写入 job log（FLAKY-RETRY 计数行）与 step summary——
   不允许无声重试。重试通过 → 记一次 flaky 事件（落盘见 3）。
2. **flaky 识别**：同一测试在相同 head 上"失败→重试通过"= 1 次 flaky 事件；
   事件计数追加到仓库 `tests/flaky-ledger.jsonl`（append-only，PR 内由 CI
   写入 run artifact + PR comment 入账）。窗口 `flaky_window_days`（默认 30）
   内事件 ≥ `flaky_threshold`（默认 3）→ 自动开 issue 列入隔离候选，人确认
   后走 ADR 进隔离清单。
3. **隔离清单**：`tests/quarantine.yaml`（每仓）——条目含 test id、owner、
   `expires`（≤ `quarantine_max_days`，默认 30 天）、ADR 引用。隔离的测试
   从 gate 判定排除但单独汇报（job log QUARANTINED 段）。**过期自动回炉**：
   周期任务（flaky-sweep）扫描全部受管仓的清单，`expires` 已过 → 从清单移除
   （回炉重新参与 gate）+ 开升级 issue。**清单变更走 ADR**：quarantine.yaml
   路径纳入 adr-required 的 C1 判定（CI-Workflows ci.yml caller 面）——
   无 ADR 引用的清单变更 gate 红。
4. **真回归不误放**：确定性失败重试 2 次全败 → gate 红，不产生 flaky 事件
   （flaky 事件仅在"失败→通过"转移时记录）。重试到绿通道对确定性失败天然关闭。
5. **SLI 留痕**：flaky 事件与重试计数输出结构化计数行（FLAKY-STATS），供
   P3-4（#98）gate 假红率指标消费。
6. **参数真源**：`governance/policy/testing.yaml#flaky_governance`
   （retry_max / flaky_window_days / flaky_threshold / quarantine_max_days），
   CI 侧拉取失败 = fail-closed 红（同 test-integrity 模式）。

## 后果

- 假红不再唤人：重试入账自动消化；真回归重试后仍红、不产生 flaky 记录。
- 隔离是"带保质期的缓刑"而非流放：到期自动回炉 + 升级 issue。
- 隔离清单作为新的"作弊面"被 adr-required 机器覆盖（与 test-integrity 的
  逃生门同机制，ADR-0035）。
- 测试框架差异（pytest -x / go test -run 重跑粒度）由 check.yml 的 runner
  适配层处理，本 ADR 只约束语义与上限。