# ADR-0046: gate 定义上移至 org required workflows（P3-1 枢轴）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0046-org-required-workflows-gate.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

gate 定义上移 org required workflows：org-gate.yml 落中心仓钉完整 SHA（PR 掏空本地 gate 的自审路径关闭）；中心/本地双轨并存观察（≥10 PR 100% 一致后退役本地轨）。
