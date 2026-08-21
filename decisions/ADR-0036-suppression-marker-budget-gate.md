# ADR-0036: 抑制标记预算门——豁免配额化与总量棘轮（P2-2）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0036-suppression-marker-budget-gate.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

抑制标记预算门：标记全集落 policy（noqa/type:ignore/gitleaks:allow 等正则+文件类），单 PR 净增>3 红、全仓总量棘轮只降不升；越界走 ADR 逃生门并负棘轮同步义务。
