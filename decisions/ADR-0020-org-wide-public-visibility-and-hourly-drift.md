# ADR-0020: 组织全仓公开政策与可见性小时级漂移检测（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0020-org-wide-public-visibility-and-hourly-drift.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

组织全仓公开政策（无可见性豁免路径，私有须新 ADR 推翻）+ drift-check §7 双向升级（申报侧 policy 校验+线上全量遍历不依赖申报完整性）+ 检测频率升每小时。
