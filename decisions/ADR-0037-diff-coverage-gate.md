# ADR-0037: diff coverage 门槛——PR 变更行覆盖率门禁（P2-3）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0037-diff-coverage-gate.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

diff coverage 门 80%：PR 变更行（merge-base diff +行）∩覆盖行，lcov/istanbul/Cobertura/go covprofile 四格式统一解析；阈值真源 .github policy，业务仓不得自行放宽；X-01 全局口径维持拒绝。
