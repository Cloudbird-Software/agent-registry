# ADR-0001: 建立 agent-registry，四类声明统一落盘（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0001-agent-registry-establishment.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

建立 agent-registry 单一真源仓，四类声明（agents/skills/tools/teams）+ models.yaml 落盘，L0→L3 分层只以 id 引用，注册条目 proposed→approved 必须走 PR。
