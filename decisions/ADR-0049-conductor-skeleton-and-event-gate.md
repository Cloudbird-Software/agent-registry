# ADR-0049: conductor 状态机骨架与事件入口安全（IR-0001 W0-C3）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0049-conductor-skeleton-and-event-gate.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

conductor 状态机骨架：transitions.yaml 外置唯一定义+受限 guard 求值器（白名单变量），非授权打标/命令静默丢弃+审计行，状态标签写一律 App 令牌；W0 只开一条主通路+认领/重试。
