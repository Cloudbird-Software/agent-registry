# ADR-0011: Runner 运行时出网监控（audit 起步）与安全姿态基线

- 状态: accepted（owner 授权代理执行，2026-08-18）
- 日期: 2026-08-18
- 主题: supply_chain 敞口的运行时层补充 / Harden-Runner egress audit / OpenSSF Scorecard 周扫
- 关联: GOVERNANCE.yaml CI-4（zizmor 静态审计）、SC-1..4、AG-2；risk_posture[supply_chain]

## 背景

CI-4 的 zizmor 是**静态**审计：能拦 workflow 写法错误（`pull_request_target` 误用、未 pin、过宽 permissions），拦不住"已放行的 action 厂商被投毒后在运行时外联"（tj-actions/changed-files 模式）。2025–2026 的 Megalodon（约 5500 仓）与 GhostAction（约 3000 密钥）均为该模式。

本组织 automerge job（template-service）在 runner 上接触 `AGENT_APP_SECRET`（App 私钥 → 组织级写权限凭据），是 supply_chain 敞口里最高价值的单点；当前对该 job 的出网行为零监控、零阻断能力。

第二缺口：仓库安全姿态无外部行业基线。drift-check 只对照自定期望状态，缺标尺（分支保护、token 权限、pin 程度、依赖更新节奏等维度）。

## 决策

1. **allowlist 增补（最小粒度，非通配符）**：`step-security/harden-runner`、`ossf/scorecard-action`；使用处一律 pin commit SHA（CI-2 惯例）。
2. **egress 监控分两阶段**：
   - 阶段一（本 ADR 生效）：四个 reusable workflow（hygiene/check/dep-review/release）+ template-service automerge 的 job 首步插入 harden-runner，`egress-policy: audit`——只记录不拦截，零可用性风险，积累各 job 出网基线。
   - 阶段二（约两周后）：按 audit 日志收敛各工作流出网域名 allowlist，切 `egress-policy: block`。属确定性控制，可 blocking（符合"概率性 advisory / 确定性 gate"二分）。
3. **Scorecard 周扫**：三个公开治理仓（.github / CI-Workflows / template-service）加 scorecard 定时扫描（周一 05:00/05:30/06:00 UTC，与 governance-drift 03:00 错峰），SARIF 进 Security tab。**不进 gate**——姿态类指标 advisory，作趋势基线。
4. **范围声明**：socket（恶意包检测）与 qodo（模型族独立 reviewer）为 GitHub App 形态，由 owner 网页安装到 selected repos，不属于本 ADR 的仓库变更范围。

## 后果

- 每个 job 增加约 5 秒（audit 模式开销）。
- 切 block 时需维护每工作流出网域名 allowlist（相关 PR 描述已给出起点清单）。
- Scorecard 初期得分可能不高（Fuzzing、Binary-Artifacts 等维度未覆盖）——按趋势看，不作 gate，不追求满分。
- `curl | sh`（uv 安装器）与 gitleaks latest-release 下载属既有链路，本 ADR 只加运行时可见性；版本钉死另行处理。
- 本 ADR 由 owner 授权 AI 代理提 PR 并以 admin 合并（flows.governance_change C1：PR + ADR 即授权凭证，owner 事后可在 retro 中复核）。
