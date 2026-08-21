# ADR-0051: 找活协议——AGENTS.md 标准块与 ghcb next/claim

- status: accepted（2026-08-21）
- 背景: IR-0001（.github#128）W0-C5 工作卡 .github#134
- 关联: spec BEH-08、IFACE-08、AC-2（陌生 agent 仅读 AGENTS.md 完成找活/认领/
  开工）、CG-1（AGENTS.md ≤30 行索引型）、ADR-0044（ghcb 令牌通道）、
  ADR-0047（state:ready 标签）、ADR-0049（/claim 转移与守卫）

## 背景

"任意本地 coding agent 打开任一产品仓，仅读 AGENTS.md 即可找到可认领的卡、
认领、开工"（IR 验收#2）要求协议有一个零文档依赖的入口：agent 不读治理仓、
不读 spec，只读所在仓的 AGENTS.md 就知道三件事——怎么找活、怎么认领、怎么
本地复现关卡。

## 决策

1. **AGENTS.md 标准块**（≤30 行约束内的固定节，template-service 与 .github
   仓同步携带；新仓经模板继承）：三命令协议——
   - `ghcb next`：列出本仓 `state:ready` 的卡（title/编号/AC 摘引）；
   - `ghcb claim <n>`：以当前身份在卡上评论 `/claim`（conductor 校验先到先得
     并置 `state:in-progress`，ADR-0049 T3）；
   - `make gates-pr`：本地复现 CI 同一套关卡（W1-C5 交付 Makefile 封装；W0
     在标准块中先行声明入口语义）。
2. **ghcb 扩展**（.github 仓 `scripts/ghcb`，保持 ADR-0044 令牌契约不变）：
   `ghcb next [repo]`（缺省=origin 所在仓；只读 gh issue 查询，无需 App 令牌，
   用调用方自己的 gh 凭据）；`ghcb claim <n> [repo]`（等价
   `gh issue comment <n> --body /claim`——认领动作本身走 conductor 校验，
   ghcb 不持有状态写权）。原 `ghcb <repo>` 铸令牌用法不变。
3. 认领合法性由 conductor guard（ADR-0049）承担：author_association∈
   {OWNER,MEMBER,COLLABORATOR} 或 agent；匿名（NONE）不可认领。ghcb 不做
   二次鉴权（单一真源）。
4. **验证形态（W0）**：在 conductor 已就位的 .github 仓放演示卡实测——冷
   上下文 agent 仅按 AGENTS.md 指引执行 `ghcb next` → `ghcb claim` → 按卡
   开工开 PR（AC-2/W0-C5 验收）。产品仓的 conductor 事件面随后续波次接入，
   template-service 先落标准块（模板继承面）。

## 后果

- 找活入口收敛到一条命令；AGENTS.md 保持索引型（CG-1），无阈值/规则正文
  （可判定规则只进 CI 关卡——INV-05）。
- ghcb next/claim 是薄封装：全部语义在 conductor（状态机）与 GitHub labels
  （状态载体）上，客户端无状态可漂移。
- 风险：gh 凭据缺失时 agent 无法 claim——错误信息直接指向 `gh auth login`。
