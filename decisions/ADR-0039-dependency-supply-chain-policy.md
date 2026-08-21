# ADR-0039: 依赖供应链 policy 落地——dep-review 从"跑了"升级为有具体 policy（P2-5）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0039-dependency-supply-chain-policy.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

依赖供应链 policy：许可证改白名单拒绝式、新增依赖包龄<90 天硬红、幻觉包 registry 404 硬红、低下载/单维护者/install 脚本需 ADR、manifest↔lockfile 静态一致性+各仓 frozen 安装执法。
