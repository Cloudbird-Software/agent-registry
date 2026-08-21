# ADR-0057: 管家骨架——唤醒矩阵前三行 + 审计日志 + dead-man 心跳 fail-closed（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0057-butler-skeleton-wake-matrix.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

管家骨架：唤醒矩阵前三行落地（6h reconcile/15min 账本刷新/1h 预算检查）+ dead-man 心跳 ping/trip 双侧（缺席即停自动合并）+ 统一审计形态 butler-audit.sh 与策略真源 butler.yaml。
