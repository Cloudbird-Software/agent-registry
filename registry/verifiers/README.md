# registry/verifiers —— T2 verifier 执照面（宪法 §4C 持证上岗 / ADR-0072）

- 条目 = 执照：**入职考试全过才有条目**。登记前置校验：
  `python3 scripts/verifier-license.py --entry registry/verifiers/<id>.yaml --results <成绩存档.jsonl>`
  （成绩存档来自 CI-Workflows `verifier-exam` workflow 的 `verifier-exam-results`
  artifact，键=`judge_id@exam_version@prompt_hash12`——存档声明见 archive
  `evalsets/verifier-exam/README.md`）。
- 条目 schema：`registry/schemas/verifier-license.json`（成绩引用/标注负债申报/
  shadow 纪律为必填结构）。
- 规则要点（ADR-0072 决策 2/5/6）：
  - replay 回放成绩**不可注册**（零真实 LLM 的管道自测≠判官能力证据）；
  - 任一考试分项不过=拒上岗=无条目；
  - 标注负债申报必填（annual_hours≥1 + committed）——未配预算不许从 T3 迁移；
  - 新发执照一律 `enforcement.veto=false`（shadow 起步；升 veto 走宪法 §5 信任门）；
  - 换模型/改 prompt 即重考=新执照条目（旧条目保留档案可追溯）。
- 首版（2026-08-22，W5-C3）：目录无条目——尚无真实判官通过 api 模式考试
  （本卡零真实 LLM 纪律）。首个条目=首个 dispatch(api) 全过考试后由上述脚本
  校验后登记。
