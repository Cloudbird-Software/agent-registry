# ADR-0048: 第一期模型接入直连 provider API（AR-3 的第一期形态）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0048-phase1-direct-provider-api.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

第一期模型接入直连 provider API（gateway 运维成本大于收益的 owner 裁定）：key 只存 org secret LLM_API_KEY，一切调用经计量 wrapper（无计量不算成功），alias 以 pipeline/models.yaml 角色档实现；附回切触发条件清单。
