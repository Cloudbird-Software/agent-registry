# ADR-0049: conductor 状态机骨架与事件入口安全（IR-0001 W0-C3）

- status: accepted（2026-08-21）
- 背景: IR-0001（.github#128）W0-C3 工作卡 .github#132
- 关联: spec INV-02/INV-09（事件入口安全）、IFACE-03（转移表）、BEH-01/BEH-08、
  AC-11（负向测试）、DECISION-04（label 为状态载体）、DECISION-05（conductor
  放 .github 仓）、ADR-0046（org-gate 双轨）、ADR-0047（state 标签全集）

## 背景

意图签署（`state:ir-signed`）后系统必须无人路由地进入 spec 阶段（BEH-01），
且一切状态转移的入口必须校验身份——否则任意成员打一个标签就能驱动流水线
（INV-02）。W0 只需一条通路（ir-signed → spec-author），但安全语义必须全量：
这决定后续所有波次的入口都长在同一个骨架上。

## 决策

1. **转移表外置**：`governance/transitions.yaml`（IFACE-03 schema：
   `{from_state, event, to_state, action, guard}`）是状态机唯一定义；conductor
   workflow 只解释不内嵌。guard 布尔表达式的变量白名单：`sender_role` /
   `author_association` / `label_set`，由内置受限求值器（无内建、白名单变量
   注入）执行；表自身是 C1 资产（改表=改治理）。
2. **conductor workflow** 落 .github 仓 `.github/workflows/conductor.yml`（本
   ADR 落地时仅监听本仓 issues.labeled / issue_comment；跨仓事件面随产品仓
   接入在后续波次扩展，W0 验收路径在本仓）。per-issue concurrency group
   （cancel-in-progress=false）；转移以 {issue, from_state, to_state} 为幂等键
   ——当前态不匹配 from_state 即 no-op，重复投递天然去重（INV-09）。
3. **事件入口安全（INV-02/09 落地形态）**：
   - `sender_role` 判定不硬编码用户名——owner 集 = `GET /orgs/{org}/members
     ?role=admin` 的 API 结果（drift-check §9 保证 admin 唯一）；agent =
     `cloudbrid-agent[bot]`；其余为 none。
   - 非授权的 `state:*` 打标或 `/start`：**静默丢弃**——回退标签、不评论、
     不启动任何阶段（防评论轰炸），审计行（时间戳/issue/actor/动作/verdict）
     写入 workflow run 日志（AC-11 的审计面）。
   - 状态标签的**写**一律以 cloudbrid-agent App 令牌执行（GITHUB_TOKEN 身份
     不持有状态标签写权——INV-02 的字面满足）；App 令牌按 AG-2 单仓作用域、
     1h 过期、磁盘不落长期凭据。
4. **W0 转移集**（只开一条主通路 + 认领/重试）：
   - `ir-draft --label:state:ir-signed--> spec`（action: invoke:spec-author，
     guard: sender_role∈{owner,agent} 且 type:intent 在 label_set）
   - `ir-signed --comment:/start--> spec`（同 guard 收紧 owner）
   - `ready --comment:/claim--> in-progress`（action: claim，guard:
     author_association∈{OWNER,MEMBER,COLLABORATOR} 或 agent；先到先得=当前
     态须为 ready，否则 no-op）
   - `quarantine --comment:/retry--> ready`（guard: owner/agent）
   未列转移一律 no-op（含反向/跳态）。
5. spec-author 调用钉 CI-Workflows 发布 tag 的 commit SHA（供应链，同
   gate.yml 钉 hygiene.yml 的惯例）；失败在原 issue 评论原因（BEH-01）。
6. **g060 锁定集暂以 CODEOWNERS owner-only 过渡**（conductor.yml +
   transitions.yaml；机器防篡改随 W1-C3 lock-tests 落地——spec INV-03 的
   分期实现）。

## 后果

- 状态机成为数据：加通路=改 YAML 走 C1 PR，conductor 代码不动。
- 负向测试（AC-11）成为验收硬门（DECISION-06④）：非 owner 身份（用
  github-actions[bot] 作非授权身份）打标必须被回退且无评论。
- 风险：github.event.comment.body 进入 guard 求值上下文前只做精确匹配
  （/start、/claim、/retry 白名单），不进任何 eval——注入面为零。
