# ADR-0007: agent 原型分类（archetype）与三层验证链（墓碑）

- status: accepted
- lifecycle: superseded
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0007-archetype-verification-chain.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

archetype 七分类（builder/checker/orchestrator/curator/interface/observer/operator）+ 三层验证链（agent 内 guardrails/team 内独立 checker/team 外审计）+ no-self-test 禁则。
