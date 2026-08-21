# ADR-0011: Runner 运行时出网监控（audit 起步）与安全姿态基线（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0011-runtime-egress-monitoring-and-scorecard.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

Runner 运行时出网监控起步（四个 reusable workflow+automerge 首步插 harden-runner audit，阶段二收敛 allowlist 切 block）+ OpenSSF Scorecard 周扫三治仓（advisory 不进 gate）。
