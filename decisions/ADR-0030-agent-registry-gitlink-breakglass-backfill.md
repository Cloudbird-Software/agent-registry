# ADR-0030: agent-registry gitlink 误入事件的破玻璃回填（60bd155 + e9424d2）（墓碑）

- status: accepted
- lifecycle: archived
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0030-agent-registry-gitlink-breakglass-backfill.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

agent-registry gitlink 误入直推（60bd155 加入/e9424d2 移除）定性破玻璃回填：gitlink 曾封死全部 PR 的 base 检出（CI 死锁），解锁唯一路径=破玻璃直推；确立同型事件处置范式。
