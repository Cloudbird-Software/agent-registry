# ADR-0004: 团队分 ephemeral/persistent，销毁前强制资产移交（handoff）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0004-team-lifecycle-handoff.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

团队分 ephemeral/persistent 两类；ephemeral 销毁前必须完成 handoff 动作清单（artifacts-pr/memory-distill/skill-extract 等），destroy_policy: after-handoff。
