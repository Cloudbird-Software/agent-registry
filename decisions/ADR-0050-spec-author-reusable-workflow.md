# ADR-0050: spec-author 可复用 workflow（冷上下文 + 注入防线 + 计量）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0050-spec-author-reusable-workflow.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

spec-author 可复用 workflow：冷上下文（全程仅 IR 标题正文+spec 模板两个输入）、IR 正文定界符包裹注入防线+spec-check 结构/注入双扫（不过校验无 PR 产出）、角色档解析+计量回写。
