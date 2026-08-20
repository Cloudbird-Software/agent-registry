# ADR-0046: gate 定义上移至 org required workflows（P3-1 枢轴）

- status: accepted（2026-08-20）
- 背景: .github issue #81 §3.3 / 工作卡 #95（P3-1，枢轴）
- 关联: CI-Workflows `.github/workflows/org-gate.yml`（新增）、org ruleset
  `org-required-workflows`（新增）、governance/rulesets/org-required-workflows.json、
  drift-check §15（新增对账）、ADR-0032（严格断言语义）、ADR-0034（§12 活体）、
  ADR-0035..0043（P2 各门——本卡聚合其入口）、ADR-0029/0031（auto-merge 链路）

## 背景

`pull_request` 事件使用**包含 PR 变更的** workflow 定义——被审仓库的 PR 可以掏空
自己的 gate（保留 job 名 `gate`、删光断言），required check 照样绿。此前唯一防线
是 `.github/` 属 C1 → owner-merge（人）——这正是要拆的人类瓶颈。#81 §3.3 给出
A/B 两案，本 ADR 采用 **A**：org ruleset 的 required workflows 规则把 gate 指向
中心仓 CI-Workflows 的固定 commit——审判逻辑来源不再是被审仓库自身。

API 实测（2026-08-20）：org 级 `workflows` 规则可用，参数形态
`{path, ref, repository_id}`（repository_id=CI-Workflows 1337911551）；
ref 必须为完整 40 位 commit SHA（本 ADR 钉死，拒绝 tag/branch 可变指针）。

## 决策

1. **org-gate.yml 落中心仓**：单一 workflow 文件（required workflows 的平台
   约束），聚合：①hygiene（复用 CI-Workflows hygiene.yml@SHA——凭据扫描/大文件/
   zizmor 照扫**被审仓库**）；②adr-required（C1 路径变更须引用真实 ADR——路径集
   取组织 C1 ∪ 业务仓 C1 的保守并集，单一真源在中心文件内，被审 PR 改不到）；
   ③`gate` job = ADR-0032 严格聚合器（仅 success 放行）+ 双轨比对注记（观察期
   数据：本地 gate 与中心 gate 结论不一致时发 annotation，供 T3 分析，不改变
   判定）。
2. **org ruleset `org-required-workflows`**：`workflows` 规则指向
   `CI-Workflows@<完整SHA>:.github/workflows/org-gate.yml`；目标 = 全部受管仓
   默认分支；bypass 仅 OrganizationAdmin（与其余 ruleset 一致）。required
   status_checks 增加 `org-gate / gate`（中心轨 check 名），与本地 `gate`
   （旧轨）**双轨并存观察**。
3. **双轨观察期（T3）**：连续 ≥10 个真实 PR 两轨判定 100% 一致后才退役本地
   gate 的 required 地位（届时新 ADR 修订 required_status_checks）。观察期内
   不一致必须定位归因；org-gate 的双轨比对注记自动积累数据。
4. **对账进 drift-check §15**：required workflow 的 repository_id/path/ref
   三元组、ruleset enforcement、bypass actors 全部落盘对账——ref 被改指向别处
   （admin 通道）下一次整点检出。
5. **中心仓保护升级**：改 org-gate = 改信任根。CI-Workflows 自身已受 org
   main-protection（PR + gate + ADR 引用）管辖；本 ADR 声明 org-gate.yml 的
   变更属最高敏感级——升级 ref 钉点必须走 CI-Workflows 的版本发布流程（tag
   vN.x.y → 修订 ruleset ref + drift-check 落盘同步），禁止直接 @main。
6. **本地 gate.yml 的去留**：观察期内维持现状（required）；退役后降级为非
   required 的快捷反馈（repo 特化检查仍留在各仓 ci.yml——中心 gate 只聚审判
   语义，不替代业务测试）。

## 后果

- T1 攻击面关闭：PR 掏空本地 gate.yml 后，审判仍由中心固定 ref 执行——
  自我削弱路径失效；C1 的 owner-merge 具备取消前提（P3-2 #96 的硬依赖满足）。
- 平台语义变化点：required workflow 的 check 名为 `org-gate / gate`；
  required workflow 在被审仓库上下文运行（GITHUB_TOKEN=被审仓，checkout=
  被审仓，审计面完整）。
- 每个受管仓每次 PR/push 新增一轨 CI 分钟消耗（公开仓免费额度内）。
- 中心 gate 的 C1 路径集为保守并集：观察期若出现「中心要求 ADR 而本地不要求」
  的判定分叉，按 T3 流程归因（预期为少数 docs/ 类路径），退役旧轨前收敛。
