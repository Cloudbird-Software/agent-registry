# ADR-0034: required check 活体验证 + PR liveness 侦测（P1-4）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0034-required-check-liveness-and-pr-stuck-detection.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

drift-check §12 required check 活体验证（文本对账≠生效验证：job 改名即"零 required check"裸奔）+ §13 PR liveness 侦测（auto-merge 挂起/check 停滞/零 check 三类卡死），阈值入期望状态。
