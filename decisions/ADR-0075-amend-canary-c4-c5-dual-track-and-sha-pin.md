# ADR-0075: canary C4/C5 预期勘误——承认双轨 main-protection + SHA/双形态供应链引用（墓碑）

- status: accepted（2026-08-22）
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0075-amend-canary-c4-c5-dual-track-and-sha-pin.md
- migrated: W1-C1（ADR-0053）后续新增条目；正文已迁 archive 仓，本文件保留编号可解析性。

canary 连续红（#257）的两处预期勘误：C4 供应链入口断言由"@vN 单一形态"改为承认双合法形态（@vN | 40-hex SHA+ciw-ref 透传），与 C6 钉扎政策一致；C5 main-protection required checks 预期由单轨 ['gate'] 更新为双轨 ['gate','org-gate']（BP-2 观察期设计，退役本地轨需未来新 ADR）。选型倾向 SHA-only（不可变+可审计），但 @vN 仍合法——不断言形态统一。依据 ADR-0056 canary 设计与 BP-2 观察期运行反馈修订。
