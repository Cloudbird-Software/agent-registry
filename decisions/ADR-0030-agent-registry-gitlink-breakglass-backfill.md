# ADR-0030: agent-registry gitlink 误入事件的破玻璃回填（60bd155 + e9424d2）

- status: accepted（2026-08-20）
- 背景: drift-check §8 报告的两条 agent-registry 非 PR commit 的定性回填
- 关联: ADR-0017（.github 误入 gitlink 同型事件先例）、ADR-0025（agent-platform 立项）、
  flows.governance_change break_glass、GM-4（REPOS.yaml 组织地图，反 submodule 方案）

## 背景

2026-08-19 20:42 UTC，owner 直推 `60bd155`（"feat: OpenJiuwen 声明式规定落地方案"）
向 agent-registry main 加入 `agent-platform` gitlink（mode 160000，指向
Cloudbird-Software/agent-platform@9809b0fe）——无 .gitmodules 配套。

后果：actions/checkout 在检出 main 时 fatal（"No url found for submodule path
'agent-platform' in .gitmodules"）。agent-registry 的 gate（validate.yml）对每个 PR
双检出（std=base ref + data=head），base 检出必炸——**全部 PR 的
gate/regression/snapshot-diff 自此全红，包括任何移除该 gitlink 的修复 PR 自身**，
CI 陷入死锁；main 上的 push 工作流同样失败。

## 决策

1. **事件定性**：`60bd155` 为误入 gitlink 的破玻璃直推（与 .github 仓 ADR-0017
   附录 a 类事件同型：净变更仅为误入 gitlink，无实质内容——"落地方案"的实质
   内容并未随该 commit 进入本仓）；非授权通道的正式变更。
2. **处置**：2026-08-20 admin 直推 `e9424d2` 移除该 gitlink（破玻璃二次动用，
   解 CI 死锁——PR 通道在 main 修复前不可用，唯一可行路径）。该直推同样按
   破玻璃规则登记回填。agent-platform 为独立 L2 仓（REPOS.yaml），组织明确
   不采用 submodule 方案（GM-4 注释），移除悬空指针不删除任何内容。
3. **豁免登记**：两条 commit 均登记入 .github 仓 expected-state.json
   `direct_push_exemptions["agent-registry"]`（本 ADR 为背书）。
4. **流程教训**：base-ref 双检出结构使 main 上的任何 checkout 破坏物都会
   封死 PR 修复通道——本 ADR 不改变该结构（防削弱设计，ADR-0010 批次4），
   但确立处置范式：此类死锁的解锁 = 破玻璃直推 + 本 ADR 型回填。

## 后果

- drift-check §8 对 agent-registry 的两条 DRIFT 在豁免登记合并后转 OK；
  Shorts_Director f63baf26 直推为独立事件，不在本 ADR 范围（另案回填）。
- 破玻璃回填时限合规：60bd155（2026-08-19 20:42 UTC）与 e9424d2
  （2026-08-20）均在各自 24h 窗口内完成 ADR + 豁免登记。
- 若 "OpenJiuwen 声明式规定落地方案" 有实质内容需要进入本仓，须走正常
  PR 通道重新提交（gitlink 形式已否定）。
