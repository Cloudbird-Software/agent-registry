# ADR-0040: auto-fix 修复循环上限 + 额度/成本熔断（P2-8）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0040-auto-fix-limit-and-cost-circuit-breaker.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

auto-fix 修复循环上限 N=3（按 gate check 失败结论计数，跨崩溃持久）+ Actions 分钟预算熔断（≥80% 告警/≥100% 置 org 变量撤全部 auto-merge，复位仅人工）。
