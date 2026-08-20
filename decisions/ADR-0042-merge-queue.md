# ADR-0042: merge queue 接入（P2-7）

- status: accepted（2026-08-20）
- 背景: .github issue #81（自动合并计划）§6 工作卡 #92（P2-7）
- 关联: governance/rulesets/merge-queue.json（新增）、agent-registry validate.yml、
  template-service ci.yml、ADR-0029/0031（auto-merge 链路）、ADR-0032（EXPECTED_SKIP
  白名单——merge_group 事件的预期跳过登记义务）

## 背景

多 agent 并发提 PR 时，每个 PR 都基于旧 main 验证通过，合并顺序不同时语义冲突
直接进 main（"各自对 main 绿、合起来红"）。merge queue 把 PR 排队、按"队列前缀 +
本 PR"的虚拟合并重新验证，绿才落地；同时消除"分支需 up-to-date"导致的反复手动
update branch。硬性前提：required check 链路上的 workflow 必须订阅 `merge_group`
事件，否则队列中 check 永不上报、合并直接失败。

## 决策

1. **新 ruleset `merge-queue`**（独立于 main-protection，便于范围控制）：
   - 目标：~DEFAULT_BRANCH，仓库范围 = agent-registry + template-service
     （高活跃仓先行，观察一周后全量——全量扩围须修订本 ADR 的范围清单）
   - 规则：merge_queue（merge_method=squash；check_response_timeout 1h；
     max_entries_to_build=5；min_entries_to_merge=1——保守串行起步）
   - bypass：仅 OrganizationAdmin（与其他 ruleset 一致）
2. **workflow 侧 merge_group 订阅**：
   - agent-registry validate.yml：`merge_group: [checks_requested]`。非 PR 事件
     走 main 面校验（validate/simulate/meta-validate），PR 专属步骤（stddiff/
     adr-required）按既有 if 跳过——语义正确：ADR 引用已在入队前 PR 面验过。
   - template-service ci.yml：同触发；gate aggregator 的 EXPECTED_SKIP 增
     `merge_group` 分支 = `deps deps-audit adr-required`（dependency-review 仅
     支持 PR 事件；deps-audit 仅 push；adr-required 消费 PR title——三者均已在
     入队前的 PR 面执法，队列面验证的是组合树本体）。
3. **对账**：ruleset 落盘 governance/rulesets/merge-queue.json，drift-check §1
   既有文本对账自动覆盖（EXTRA ruleset 检查同步防漂移）。
4. **与 ADR-0032 的义务衔接**：未来任何仓加入队列 = 同步给该仓 aggregator 补
   merge_group 的 EXPECTED_SKIP 登记，漏登记的结果是 gate 红（fail-closed）。

## 后果

- 语义冲突的 PR 在队列重验时被拦（踢出+标注），main 全程绿；并发 PR 按序串行
  落地，"update branch"负担消失。
- 队列串行（min_entries=1）起步：吞吐换确定性的保守选择，观察后调。
- .github / CI-Workflows 自身暂不入队（治理仓变更频率低、owner-merge 语义
  仍在）；入队时按决策 2 的义务补触发与登记。

## 测试（T1 语义冲突拦截 / T2 merge_group 上报 / T3 并发吞吐 / T4 对账）
按卡内预设执行；T1 需要构造相互冲突的两 PR（改同函数返回类型 vs 按旧类型
调用），在 agent-registry 上以 decisions/ 文档冲突形态等价执行。
## 修订（2026-08-20）：org 级 → repo 级 ruleset

实施时实测：org rulesets API（REST 与 GraphQL）均不接受 merge_queue 规则类型
（"Invalid rules: 'Merge queue'"）；merge_queue 必须与 pull_request /
required_status_checks 同处一个 ruleset，且 merge_method 须为仓库允许的
squash（MERGE 被拒）。决策 1 修正为：

- merge queue 以 **repo 级 ruleset**（名 `merge-queue`）存在于各目标仓，
  含三个规则（pull_request / required_status_checks[gate] / merge_queue）
- 声明与对账模式对齐 P1-1 repo settings：`expected-state.json#merge_queue`
  （repos + params）为真源，drift-check §14 对账（含未声明仓私自开队列的
  EXTRA 检查），apply.sh step6 幂等修复（GraphQL 写入）
- 两仓已建（agent-registry 21076429 / template-service 21076438），参数与
  本 ADR 决策 1 一致（squash、串行保守起步）
