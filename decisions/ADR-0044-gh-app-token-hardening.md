# ADR-0044: gh-app-token.sh 加固——Windows 兼容、jq 降级可选、安装令牌缓存（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0044-gh-app-token-hardening.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

gh-app-token.sh 加固：JWT 签名改临时文件（Windows /proc fd 不可读）、JSON 工具 jq→python/node 降级链、安装令牌 600 权限 1h 缓存；ghcb 便捷入口。
