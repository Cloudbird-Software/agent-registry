# ADR-0041: post-merge 验证 + 自动 revert（P2-6，自动合并的核心安全绳）

- status: accepted（2026-08-20）
- 背景: .github issue #81（自动合并计划）§6.6 工作卡 #91（P2-6）
- 关联: .github/workflows/post-merge-verify.yml（新增）、governance/expected-state.json、
  ADR-0029/0031（P1-1/P1-2：auto-merge 全链路已通）、ADR-0033（检测链路 pipefail）

## 背景

自动合并把"事前人审"替换为"机器判据 + 事后快速回滚"。没有事后装置，无人值守
合并的坏变更要等下一次人看才发现——一人公司的真实风险不是"坏代码进了 main"，
而是"坏代码进了 main 而我三天后才知道"（#81 风险模型）。本 ADR 落地核心装置：
每次合并到 main 后自动跑 post-merge 验证，失败即自动生成 revert PR 并
auto-merge——"事前 review"由此可被"事后回滚"实质替代。

## 决策

1. **post-merge 验证 workflow**（`.github/workflows/post-merge-verify.yml`）：
   `push: branches: [main]` 触发（含 squash 合并产生的 commit），对合并结果做
   快速冒烟——治理仓的冒烟 = gate 的 main 面等价物（YAML/JSON/脚本语法 + drift
   本地自检的只读子集）+ 本次合并 PR 的门禁复核（合并 commit 关联 PR 的 required
   check 结论快照）。业务仓后续按仓注册各自冒烟（make smoke 等）。
2. **自动 revert**：验证失败 → 用 GitHub REST 生成 revert PR（POST
   /pulls/{n} 的 revert 端点不可用时走手动构造），revert PR 标题带
   `[auto-revert]` + 原因，**enable auto-merge**（gate 绿即回滚进 main）。
   revert 失败（如冲突）→ 开 P0 issue 通知 owner。
3. **防回环**：revert PR 自身触发 post-merge 验证失败时不无限 revert——
   连续 revert 深度 =1（检测到本次合并是 revert 类 commit 则只告警不再
   自动 revert）；每仓每小时最多 1 次自动 revert（workflow 内以 run 历史
   判定，超出则只开 issue）。
4. **触发面**：仅 push 到 main（PR 事件不触发）；权限最小
   contents:read + issues:write（开告警 issue）；revert PR 创建经 App
   installation token（AGENT_APP_SECRET，CI 注入）——AG-1 身份，受全部
   ruleset 约束，revert 也必须过 gate。
5. **SLI 基础**：验证结果与 revert 事件以 issue/commit 记录留痕，供 P3-4
   （#98 门禁逃逸率面板）消费。

## 后果

- 坏变更在 main 上的存活时间从"天"压缩到"验证时长 + gate 时长"（约 10 分钟级）。
- revert 是写操作且自动执行——本 ADR 将其限定在"合并后验证失败"单一触发面，
  连续深度与频率双闸；任何放宽须新 ADR。
- 治理仓首个受益仓；业务仓接入按 REPOS.yaml 逐仓注册冒烟命令（后续卡）。