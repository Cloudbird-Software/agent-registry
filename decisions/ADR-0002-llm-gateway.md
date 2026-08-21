# ADR-0002: 模型接入 = LLM Gateway 常驻服务，alias 是唯一接口（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0002-llm-gateway.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

模型接入经 LLM Gateway 常驻服务，models.yaml 只声明 alias→路由组+配额，key 一次性注入 gateway secret store；rev1 部署配置落本仓 deploy/llm-gateway 并与 alias 集合对齐校验。
