# ADR-0056: holdout 仓与泄漏诱饵（试卷层实体化）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0056-holdout-repo-and-canary.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

holdout 试卷层实体化：公开仓 + App 不安装的差异隔离（违规读取可检测而非靠保密），条目 schema 与校验器、封存/引用约定、泄漏诱饵注册+周期扫描+演习正控。
