# ADR-0054: arbiter 仲裁内核 v1——独立仓、纯 CAS 租约、无 LLM、默认拒绝（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0054-arbiter-kernel-v1.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

arbiter 仲裁内核 v1：独立最小仓（拆家原则——被审计者不得组装审计报告），纯 CAS 租约（git refs createRef 原子性）、无 LLM、默认拒绝、误放行台账；/claim 认领的原子层。
