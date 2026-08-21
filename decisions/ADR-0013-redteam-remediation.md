# ADR-0013: 红队演练修复批次——验证器元验证、防线注册表硬化与 ADR 编号唯一性（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0013-redteam-remediation.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

红队一批修复：validate.py 元验证测试套件（正向全绿+逐项负向注入）、checks 注册表硬化、adr-required check 实装转 active（CT-CUR-003 闭环）、ADR 编号唯一性机器检查（0011 双档唯一豁免）。
