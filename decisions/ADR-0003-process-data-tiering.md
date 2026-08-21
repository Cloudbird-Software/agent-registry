# ADR-0003: 过程数据三分离——声明与决策进 git，事件进数据库，轨迹进对象存储（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0003-process-data-tiering.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

过程数据三分离——声明与决策进 git、结构化事件进 JSONL→SQLite/PG、原始轨迹进对象存储滚动 30 天清理；项目仓 clone 不携带过程数据。
