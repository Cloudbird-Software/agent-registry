# ADR-0045: cloudbrid-agent App 永不持有 workflows 权限——CI 工作流变更走 owner 凭据通道

- status: accepted（2026-08-20）
- 背景: .github issue #102（App 缺 Workflows 权限阻塞 AI_Web_School T-W5-034
  gate 接线；2026-08-20 实锤：PR #47 合并时 test-freeze job 无法随 PR 提交，
  验收第 4 条红灯挂账）
- 关联: expected-state.json `github_app.must_not_have`（机器执法已存在）、
  standards/automation/app-permissions.md（本 ADR 落盘）、AG-1、
  AI_Web_School T-W5-034 / #102 的回迁 diff、ADR-0044（认证入口）

## 背景

GitHub 限制：无 workflows 权限的身份创建的 tree 一旦包含
`.github/workflows/**` 即 403（Resource not accessible by integration）。
cloudbrid-agent App（AG-1，agent 写仓唯一身份）权限为
contents/issues/pull_requests:write——**无法以 PR 形式提交任何 CI 工作流变更**。
#102 给出两条路：(1) 给 App 加 workflows 权限；(2) 政策明确永不授予，并规定
替代通道。

## 决策

1. **永不授予**：App 永不持有 workflows / administration 权限。理由：
   - 最小权限原则的实质执法——workflows:write 等于允许修改审判自己的 gate
     定义（#81 §3.3 的核心威胁模型），App 是高频自动化身份，该权限面不可接受；
   - expected-state.json `must_not_have` + drift-check §6 已是机器执法，本 ADR
     补上政策文本与人工面的决策记录。
2. **替代通道（owner 凭据通道）**：CI 工作流变更（`.github/workflows/**`）由
   owner 凭据提交——两种形态：
   - 常态：owner 本人在 UI/PAT 下提交 PR（agent 在 issue/PR 描述中以 diff 形式
     产出补丁，owner 审后 apply）；
   - owner 显式授权的 agent 会话：owner 以 PAT 授权 agent 代为提交（本次
     T-W5-034 回迁即此形态——PR 留痕、过 gate、CODEOWNERS owner-review 语义
     不变，审计面完整）。
   通道约束：变更仍必须走 PR 过 gate + ruleset——owner 凭据不豁免任何机器门禁，
     只解决「谁有权触碰 workflows 文件」。
3. **受冻结资产约束的验收脚本更新**：T-W5-034 回迁同时把
   `tools/accept/t_w5_034.sh` 第 4 条的精确字符串断言更新为含 `contract` job
   的现行 needs 列表（P2-4 ADR-0038 已并入 gate，脚本断言滞后）——按
   specs/test-freeze 体系走 [TEST-FREEZE-APPROVE] 标记 + MANIFEST 重签，
   人工批准语义由 owner 凭据通道 + CODEOWNERS 人审承担。
4. 落盘 `standards/automation/app-permissions.md` 并入 AGENTS.md 索引。

## 后果

- App 权限面保持最小；CI 工作流变更从「agent 卡死」变为「有明确替代通道」，
  #102 的阻塞解除。
- agent 未来遇到工作流变更需求：产出 diff → issue/PR 描述登记 → owner 通道
  apply；不得尝试以 App 身份直推（会 403，且属预期行为）。
- T-W5-034 验收第 4 条转绿的路径打通（test-freeze 并入 gate.needs）。
