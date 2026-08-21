# ADR-0047: 意图入口 issue form 与治理标签全集（IR-0001 W0-C2）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0047-intent-entry-and-state-labels.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

意图入口 issue form（九字段≡IR schema v1，全必填）+ 治理标签全集（10 state:*+2 type:*）进 expected-state；apply §7 幂等同步/drift §16 对账；设置权归 conductor（本 ADR 只管存在性与形状）。
