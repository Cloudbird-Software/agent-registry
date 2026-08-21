# ADR-0035: 测试篡改检测门 test-integrity（P2-1）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0035-test-integrity-gate.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

test-integrity 门（regex 级）：测试文件删除/断言计数净降/新增抑制标记/期望值改写四规则命中即红；ADR 逃生门豁免计数入账；fail-closed（base/head/policy 拉取失败一律红）。
