# ADR-0028: Use-up-Plan 应用层语言基线 Go（CI runtime 切换）

- status: accepted（2026-08-19）
- 背景仓库: Use-up-Plan
- 关联: ADR-0024（Use-up-Plan 建仓申报，其决策 4 语言栈记载由本 ADR 修正）、
  governance/policy/languages.yaml（application 层默认 Go）

## 背景

Use-up-Plan（AI 多 plan 额度管理与路由调度工具）从 template-service 派生建仓（ADR-0024），
继承模板的 TypeScript 脚手架与 node runtime CI。立项实现规划（仓内 Intent.md §9 /
docs/ROADMAP.md）确定为纯后端应用层服务：QDL 语义内核、append-only 事件账本、数值辨识
（量化似然 / LP 影子价格）与本地路由服务，无前端同构场景。

policy/languages.yaml 规定 application 层默认 Go，typescript 仅限 frontend-isomorphic
场景——ADR-0024 决策 4 按模板现状登记的 TypeScript 语言栈应予修正。

## 决策

1. 应用层语言选定 **Go 1.25.1**（languages.yaml application 层默认）；移除模板 TS 脚手架
   （package.json / tsconfig / vitest / src 等），仓库零第三方依赖起步。
2. CI 切换：check job `runtime: node` → `runtime: go`（CI-Workflows check.yml@v1，
   go-version "1.25.1"）；push 面 deps-audit 由 npm audit 换 govulncheck@v1.7.0
   （proxy.golang.org 2026-08-13 最新稳定版）——TS 脚手架移除后无 package-lock.json，
   npm audit 必红。
3. depcruise（Node 工具链依赖）由自研 tools/archlint 替代，机器执法 GO-3（main 仅在
   cmd/ 与 tools/）/ MOD-1（模块单入口）/ MOD-5（模块登记）。
4. Makefile 目标语义不变（setup / fmt / lint / arch / test / build / check），"CI 只认
   make 接口"的组织约定继续成立；dependabot npm → gomod。
5. 首批依赖提案（goccy/go-yaml MIT / gonum BSD-3-Clause / errcheck MIT / goleak MIT）
   已获 owner 批准（2026-08-19），按 Phase 逐 PR 引入。
6. 本 ADR 作为该仓首个 C1 面 PR（.github/ / AGENTS.md / Makefile / docs/ 变更）的
   adr-required 引用背书。

## 后果

- ADR-0024 决策 4 的 TypeScript 语言栈记载由本 ADR 修正；REPOS.yaml 条目未登记语言
  字段，无需变更。
- 语言更换 = 重新立项（languages.yaml language_change）。
- Use-up-Plan CI gate 在 runtime 切换前必红（node 24 跑 Go 仓 make check），对应 PR
  合并后恢复绿；merge 后 push 面 govulncheck 上线。
