# ADR-0042: merge queue 接入（P2-7）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0042-merge-queue.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

merge queue 接入：org API 不支持 merge_queue 规则→repo 级 ruleset（agent-registry/template-service 串行保守起步）；required 链路 workflow 须订阅 merge_group（EXPECTED_SKIP 登记义务）。
