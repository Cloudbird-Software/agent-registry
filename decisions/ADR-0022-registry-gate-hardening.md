# ADR-0022: 注册层门禁硬化（issue #31 审计收敛）（墓碑）

- status: proposed
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0022-registry-gate-hardening.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

注册层门禁硬化（issue #31 审计收敛 1-10）：validate.py 15 条语义防线——capability 白名单（K-Q 越权全拦）、must_run/allow 执行通道三词表、断言下限、相位可达性求解、flow_ref fail-closed、JSON Schema 语法校验等。
