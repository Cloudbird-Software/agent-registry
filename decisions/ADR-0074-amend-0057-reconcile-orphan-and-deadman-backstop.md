# ADR-0074: ADR-0057 运行反馈修订——reconcile 孤儿标签语义收窄 + dead-man 双层触发（墓碑）

- status: accepted（2026-08-21）
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0074-amend-0057-reconcile-orphan-and-deadman-backstop.md
- migrated: W1-C1（ADR-0053）后续新增条目；正文已迁 archive 仓，本文件保留编号可解析性。

W1 首轮运行反馈的两处修订：reconcile 孤儿标签检查移除（closed issue 的 state:* 是历史事实非漂移）；dead-man 双层触发（hc.io 外部告警层 + 仓内 heartbeat-watch 陈旧度自动兜底层，trip 逻辑收敛 governance/deadman-trip.sh）。
