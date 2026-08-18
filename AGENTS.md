# AGENTS.md — agent-registry

本仓是组织智能体的 single source of truth（L1 注册层）。标准（L0）在 [.github/standards/agent/](https://github.com/Cloudbird-Software/.github/tree/main/standards/agent)。改动一律走 PR；引用 `status != approved` 的条目会被 `scripts/validate.py` 拒绝。

## 硬规则

- 禁止出现任何明文密钥/连接串；一律 `env:` 引用。
- agent 只引用 models.yaml 中的 alias；模型接入必须经 LLM Gateway（ADR-0002）。
- ephemeral team 必须声明 archive_to + handoff；销毁前移交必须完成（ADR-0004）。
- 团队协作声明是可执行的：`scripts/simulate-wave.py` 是 CI required 门禁（12 场景流程彩排，退出码非 0 拒绝合并——ADR-0011）。

## 索引（用到再读）

| 场景 | 读这个 |
|---|---|
| 声明一个 agent / skill / tool / team | 对应 schema：`.github/standards/agent/*.schema.yaml` |
| 理解某原型的内部构成与职责保证 | [standards/archetype-profiles.yaml](standards/archetype-profiles.yaml) |
| 理解团队/协作/卡与流/生效机制 | [standards/team-collaboration.yaml](standards/team-collaboration.yaml)（ADR-0011） |
| owner 注意力如何被预算 | [standards/attention-ledger.yaml](standards/attention-ledger.yaml) |
| 写某个 agent 的提示词 | registry/identities/ 既有范本 |
| io_contract 输入/输出 schema | registry/schemas/*.json |
| 选模型 / 查配额档 | [registry/models.yaml](registry/models.yaml) |
| 理解某条现状的为什么 | [decisions/](decisions/) 的 ADR |
| 校验声明引用完整性 | `python3 scripts/validate.py` |
| 流程彩排（意图→交付→事故→归档） | `python3 scripts/simulate-wave.py` |
| 过程数据去向 | [decisions/ADR-0003](decisions/ADR-0003-process-data-tiering.md) | |
