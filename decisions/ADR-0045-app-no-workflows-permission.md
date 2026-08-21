# ADR-0045: cloudbrid-agent App 永不持有 workflows 权限——CI 工作流变更走 owner 凭据通道（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0045-app-no-workflows-permission.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

cloudbrid-agent App 永不持有 workflows/administration 权限（must_not_have 机器执法）；CI 工作流变更走 owner 凭据通道（diff 产出→owner 审后 apply，仍必须过 PR+gate）。
