# ADR-0041: post-merge 验证 + 自动 revert（P2-6，自动合并的核心安全绳）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0041-post-merge-verification-and-auto-revert.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

post-merge 验证 + 自动 revert PR（合并后冒烟失败即生成 [auto-revert] PR 并 auto-merge；连续 revert 深度=1、每仓每小时 1 次双闸）——"事后回滚"实质替代"事前人审"的安全绳。
