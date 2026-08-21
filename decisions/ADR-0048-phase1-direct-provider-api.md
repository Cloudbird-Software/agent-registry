# ADR-0048: 第一期模型接入直连 provider API（AR-3 的第一期形态）

- status: accepted（2026-08-21）
- 背景: IR-0001（.github#128）spec DECISION-01；W0-C1 工作卡 .github#130
- 关联: GOVERNANCE.yaml AR-3（修订对象）、ADR-0002 rev1（llm-gateway 部署）、
  specs/IR-0001/ADR-draft-ar3-phase1-direct-api.md（随 spec PR #129 评审的草案，
  本 ADR 为其正式化）、INV-06/BEH-09（计量与审计条款）、ASSUMPTION-01
  （连通性监控）

## 背景

AR-3 的意图有三：① agent 声明与 provider 解耦（alias 间接层）；② 明文 key
不出现在仓库/配置；③ 用量可按团队计量、配额可控。llm-gateway（LiteLLM，
ADR-0002）是满足全部三条的实现，但它要求一台常驻机器（VPS/家用盒/NAS）。
GitHub 生态内不存在免费托管持久服务的途径（Actions 不能当服务器）；免 VM
的 serverless 替代品缺少 per-team 虚拟 key 配额能力，且引入新的外部服务
依赖。owner 裁定（spec DECISION-01）：第一期的运维成本大于收益。

## 决策

第一期（自本 ADR 生效起，至"回切触发条件"任一满足止）：

1. 模型接入允许直连 provider API（OpenAI 兼容 `/chat/completions`）；
   provider key 只存 org secret `LLM_API_KEY`（登记
   `expected-state.json#org_secrets_required`，drift-check §5 执法存在性；
   值仍由 admin 在网页/CLI 设置——apply.sh 不触碰 secret 值的一贯纪律），
   仓库/agent 配置/声明零明文 key 的要求不变（AR-3 意图②保留）。
2. 一切 LLM 调用必须经计量 wrapper（CI-Workflows `scripts/llm-call.sh`）：
   逐次落盘 model/prompt 版本哈希/seed/采样参数/用量/时延/HTTP 状态，输出
   过 `scripts/llm-usage.schema.json` 结构自检——自检不过 = 调用失败
   （fail-closed：无计量不算成功；意图③降级为"只计量不熔断"，数据保留供
   后续预算化，BUDGET-04）。
3. alias 间接层（意图①）以 `pipeline/models.yaml` 的"角色档 → 具体模型 +
   采样参数"解析表实现（W0-C4 交付），版本化、改动走 PR；agent 声明仍只
   引用角色档，不直写 provider 模型名。registry/models.yaml 的 alias 语义
   与 AR-8 族级独立要求继续有效。
4. 连通性监控（ASSUMPTION-01）：CI-Workflows
   `.github/workflows/llm-connectivity.yml` 每 6h 一次最小调用（max_tokens=1），
   runner 出向白名单仅 github + provider 域名（harden-runner egress block，
   INV-06 第一期形态）；失败即红 = provider 不可达或 key 失效。

## 回切触发条件（任一满足即重启 gateway 评估）

- 需要 per-team/per-agent 配额或预算熔断；
- 需要多 provider failover；
- 需要按角色档的成本归账（wrapper 计量显示成本结构失控）；
- 组织有了事实上的常驻机器。

## 后果

- 正面：零新增基础设施，编排闭环（W0-C3/C4）可立即开工；计量数据不丢，
  回切无障碍。
- 负面：无集中 kill switch（只能靠轮换 org secret）；无配额硬限制（只有
  事后计量）；provider key 暴露面从 gateway secret store 变为 GitHub org
  secrets + Actions runner 内存。
- 缓解：key 轮换流程文档化；cost-check 的 LLM 预算通道数据源改为 wrapper
  落盘的 usage 汇总（原定 pending 项的替代实现）；GOVERNANCE.yaml AR-3
  条文同步标注第一期形态（与本 ADR 双向引用，CI 校验一致性）。
