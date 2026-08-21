# ADR-0029: 仓库级 auto-merge 纳入期望状态对账（自动合并计划 P1-1）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0029-allow-auto-merge-reconciliation.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

allow_auto_merge 纳入 expected-state repo_baseline 全仓对账（drift-check §4 断言+apply.sh step5 幂等修复；字段读不到按漂移 fail-closed）——开关静默掉落即自动合并全链路失效的盲区关闭。
