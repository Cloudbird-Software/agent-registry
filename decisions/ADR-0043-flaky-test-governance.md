# ADR-0043: flaky 测试治理——重试入账、识别、带过期隔离（P2-9）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0043-flaky-test-governance.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

flaky 治理：失败自动重试≤2 且每次入账；仅"失败→通过"转移计 flaky 事件（确定性失败重试后仍红不产生记录）；隔离清单带过期自动回炉，清单变更走 ADR。
