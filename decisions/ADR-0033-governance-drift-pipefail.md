# ADR-0033: governance-drift 检测步骤 pipefail 修复（GM-1 漂移报警机制失效）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0033-governance-drift-pipefail.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

governance-drift 检测步骤加 set -o pipefail——bash -e 下 `drift-check | tee` 管道退出码恒 0 曾致"漂移自动开 issue"机制整体失效（run 32331351942 实证）。
