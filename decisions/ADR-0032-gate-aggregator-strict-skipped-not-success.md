# ADR-0032: gate aggregator 严格化——skipped ≠ success + workflow 级路径过滤禁令（P1-3）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0032-gate-aggregator-strict-skipped-not-success.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

gate aggregator 严格化：result != "success" 即红（skipped/cancelled/timed_out 全红），结构性预期跳过以 EXPECTED_SKIP 白名单显式登记，required 链路禁 workflow 级 paths 过滤。
