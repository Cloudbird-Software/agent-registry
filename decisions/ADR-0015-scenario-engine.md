# ADR-0015: 场景引擎与测试底层方法统一（墓碑）

- status: proposed
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0015-scenario-engine.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

场景引擎与测试底层方法统一：一切测试=事件进→事件出→断言不变式；scenarios.yaml 声明式断言（A1-A7 原语+op 五种）+ CT 双层链接（scenario 声明层先决/runtime 三分类）。
