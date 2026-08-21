# ADR-0058: Shorts_Director 直推 f63baf26 追认回填（GM-2 §8 豁免登记）

- status: accepted（2026-08-21）
- 背景: drift-check §8 直推检测报 P0（超 24h 回填时限）；IR-0001 W0 收尾的漂移清零
- 关联: GOVERNANCE.yaml GM-2（治理仓变更分级/破玻璃）、ADR-0017（直推豁免登记
  机制先例）、expected-state.json#direct_push_exemptions

## 背景

`Cloudbird-Software/Shorts_Director` 默认分支存在非 PR 直推 commit
`f63baf264291670aa33f4a599779dd5c84678433`（randypanding，2026-08-19T17:39:51Z，
"feat(entity): Shot 实体、生命周期 FSM 与 IV-SH 不变量"，4 文件 +486 行）。
policy_effective=2026-08-19T00:00:00Z 当日直推，drift-check §8 于 IR-0001 W0
治理值守全面运转后（2026-08-21）首次完整扫描时检出并按超时报 P0。

## 决策

1. **追认定性**：该 commit 为正常功能开发（非紧急回滚破玻璃），发生时点
   （生效日当天傍晚）W0 治理流水线尚未运转、直推检测尚未覆盖——属流程空窗
   而非绕过审查。内容自那时起已在 main 上被后续 PR 延续使用，回滚无意义。
2. **豁免登记**：按 §8 豁免机制（ADR-0017 附录形态）将完整 SHA 登记进
   `expected-state.json#direct_push_exemptions.Shorts_Director`，drift-check
   对账后 P0 消除。这不是追认破玻璃（GM-2 破玻璃仅限紧急回滚），是空窗期
   历史事实的登记——与建仓 bootstrap 类豁免同类。
3. **防再发**：Shorts_Director 受 org main-protection（PR+squash）约束，
   后续直推将被 ruleset 直接拒绝（该直推发生于 ruleset 全量生效前）。

## 后果

- §8 直推漂移清零；豁免清单保持"逐完整 SHA、ADR 背书、新直推不可能搭便车"
  的不变量。
- 本 ADR 即 GM-2 要求的回填记录；无代码变更。
