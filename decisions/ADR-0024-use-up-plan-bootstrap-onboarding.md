# ADR-0024: Use-up-Plan 建仓申报与 bootstrap 直推豁免登记

- status: accepted（2026-08-19）
- 背景仓库: .github / Use-up-Plan / agent-registry
- 关联: ADR-0021（bootstrap 直推豁免机制）、GOVERNANCE.yaml GM-4/flows.new_repo、expected-state.json direct_push_exemptions

## 背景

Use-up-Plan 于 2026-08-19T09:51Z 由 owner 从 template-service 派生创建（AI 多 plan
额度管理与路由调度工具立项，意图见仓内 Intent.md）。建仓时序上分支/PR 尚不存在，
两个 commit 不可能走 PR，属 ADR-0021 已裁定的建仓 bootstrap 类直推：

1. `ba75401f84eb915a119568c246168d8cdb8a1200`（2026-08-19T09:51:14Z，"Initial
   commit"）——模板派生的初始 commit，建仓后 4 秒产生；
2. `82132afc169a54b98869df136d1d6235124c4a96`（2026-08-19T09:52:13Z，
   "Create Intent.md"）——GitHub UI 建仓附带的内容编辑 commit（ADR-0021 (b) 类
   先例：Shorts_Director/Script_Writer 同款）。

该仓当时未申报入 governance/REPOS.yaml，被 drift-check §7b/§8 检出（3 项漂移）。
本 ADR 按 flows.new_repo 收口：申报入图 + 直推逐完整 SHA 登记 exemption。

## 决策

1. **申报入图**：REPOS.yaml 增 Use-up-Plan 条目——layer L2、visibility public、
   status active；角色：AI 多 plan 额度管理与路由调度工具（额度审计/规则标准化
   描述/最优分配求解/实时切换；立项意图见 Intent.md，README 待首个正式 PR 脱离
   模板文案）。
2. **直推豁免登记**：expected-state.json direct_push_exemptions 增
   Use-up-Plan 上述两完整 SHA（ADR-0021 (b) 建仓 bootstrap 类；新直推不可能
   搭便车——逐 SHA 登记仍为唯一通道）。
3. **平台配套补全**（flows.new_repo step2 等价物，已随本 ADR 执行）：squash-only/
   删分支基线（apply.sh 已覆盖）、wiki/projects 关闭、production environment
   （required reviewer=owner + 仅受保护分支，RL-1）、cloudbrid-agent 安装挂载
   （AG-4）。仓内 gate/automerge/scorecard/CODEOWNERS/dependabot 由 template-service
   派生自动继承（CI-1/CI-4/SC-3/CG-2）。
4. **后续要求**：README 仍为 template-service 模板文案，首个正式 PR 须替换为项目
   自述；语言栈为 TypeScript（template-service node runtime），符合
   policy/languages.yaml application 层准入（typescript 限前端同构场景由该仓
   AGENTS.md/docs 约束）。

## 后果

- drift-check §7b（未申报）与 §8（直推）对 Use-up-Plan 的 3 项漂移消除；
- 该仓自首个 PR 起受 main-protection（gate required）约束，直推将再次被 §8 检出
  且无新增豁免通道；
- 本 ADR 不改变 ADR-0021 豁免清单既有条目。
