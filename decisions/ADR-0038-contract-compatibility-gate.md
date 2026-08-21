# ADR-0038: 契约兼容性检测门——OpenAPI breaking + JSON Schema breaking + DB migration 前后兼容（P2-4）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0038-contract-compatibility-gate.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

契约兼容门：OpenAPI breaking（oasdiff --fail-on WARN 从严）+ JSON Schema breaking 结构分类器 + destructive DDL 检测（ADR 引用+回滚脚本逆操作双要求）；policy 失明防护（声明路径零命中即红）。
