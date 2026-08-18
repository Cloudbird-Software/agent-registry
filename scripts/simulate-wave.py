#!/usr/bin/env python3
"""simulate-wave.py —— 团队协作声明的确定性流程模拟器（team-collaboration v1.0）。

目的：把声明当作可执行规范走查（walkthrough）。不是单测，是"流程彩排"——
从人类意图到交付到事故，逐步推进相位状态机，对每一步断言：
  A1 actor 存在   该步的执行者（seat 在场 or service/机制已激活）在声明中有定义
  A2 权限合法     执行者的 scope / capabilities.allow 覆盖该步动作（动作词 ∈ side-effects 词表）
  A3 注意力有账   owner 阻塞点在 attention-ledger 有登记且有默认动作
  A4 预算有归属   消耗预算的动作有池归属；升级不计入发起方
  A5 事件有生产者 引用的事件有声明生产者（flow.event_producers / output_event）
  A6 相位转移合法 flow.phases.graph 中存在对应边
  A7 留痕完整     每步产出一个事件且事件名有生产者（trace_id 贯穿——模拟 trace 即事件流）

一切输入来自 standards/ 与 registry/（无硬编码流程）——任何 AI 复跑结果一致。
退出码非 0 = 存在声明缺陷（CI 拒绝；validate.yml 双侧运行）。
REGISTRY_DATA_ROOT：CI 中标准侧（本脚本所在 ref）审数据侧（PR head）的 registry。
"""
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("REGISTRY_DATA_ROOT", ROOT))
REG = DATA / "registry"


def load(p):
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


TC = load(ROOT / "standards" / "team-collaboration.yaml")
LEDGER = load(ROOT / "standards" / "attention-ledger.yaml")
PROFILES = load(ROOT / "standards" / "archetype-profiles.yaml").get("profiles", {})
SIDEEFFECTS = load(ROOT / "standards" / "side-effects.yaml")
FLOWS = load(ROOT / "standards" / "flows.yaml")
CHANGECLASSES = load(ROOT / "standards" / "change-classes.yaml")
MODELS = {m.get("alias"): m for m in load(REG / "models.yaml").get("models", [])}
ACT = TC.get("activation", {})
AGENTS = {p.stem: load(p) for p in (REG / "agents").glob("*.yaml")}
TEAMS = {p.stem: load(p) for p in (REG / "teams").glob("*.yaml")}

errors = []
trace = []


def log(step, msg):
    trace.append(f"  [{step}] {msg}")


def check(cond, code, msg):
    """断言：失败记缺陷，不中断（走完全流程暴露全部缺陷）。"""
    if not cond:
        errors.append(f"{code}: {msg}")
    return cond


# ── 声明派生的查询 ────────────────────────────────────────────────────────
SEAT_PHASES = (TC.get("seats") or {}).get("present_in_phases") or {}
GRAPH = ((TC.get("flow") or {}).get("phases") or {}).get("graph") or []
EVENT_PRODUCERS = (TC.get("flow") or {}).get("event_producers") or {}
SERVICES = TC.get("services") or {}
TEAMS_STD = TC.get("teams") or {}
SCOPES = TC.get("scopes") or {}
VOCAB = set()
for _grp in (SIDEEFFECTS.get("groups") or {}).values():
    VOCAB.update(_grp.keys())


def seat_present(seat, phase):
    """座位在该相位是否在场。"""
    spec = SEAT_PHASES.get(seat) or {}
    phases = spec.get("phases")
    if phases == "any":
        return True
    return phase in (phases or [])


def archetype_of(seat):
    return {"planner": "planner", "test_author": "test-author", "builder": "builder",
            "researcher": "researcher", "curator": "curator", "adversary": "adversary",
            "responder": "responder", "deployer": "deployer"}[seat]


def seat_agent(seat, team):
    """团队声明中该座位的 agent 实例（按 seat 字段；兜底按 archetype）。"""
    for m in team.get("members", []):
        if m.get("seat") == seat:
            return str(m.get("agent", "")).removeprefix("agent:")
    want = archetype_of(seat)
    for m in team.get("members", []):
        aid = str(m.get("agent", "")).removeprefix("agent:")
        if AGENTS.get(aid, {}).get("archetype") == want:
            return aid
    return None


def agent_allow(archetype, agent_id=None):
    """原型（或实例）的 capabilities.allow。"""
    if agent_id and agent_id in AGENTS:
        return set((AGENTS[agent_id].get("capabilities") or {}).get("allow") or [])
    return set(((PROFILES.get(archetype) or {}).get("capabilities") or {}).get("allow") or [])


def phase_edge_ok(frm, event_key):
    """A6：相位图中存在 from→* 且事件匹配的边（any 边视为通配）。"""
    for e in GRAPH:
        if str(e.get("from")) in (frm, "any") and event_key in str(e.get("when", "")):
            return e
    return None


def owner_blocking_registered(item):
    """A3：阻塞点在账本任一分类有登记。"""
    for bucket in ("synchronous", "asynchronous", "sampled", "auto"):
        for entry in LEDGER.get(bucket) or []:
            if isinstance(entry, dict) and entry.get("item") == item:
                return bucket
            if isinstance(entry, str) and item in entry:
                return bucket
    return None


def event_has_producer(event_key):
    """A5/A7：事件有生产者（event_producers 表或服务 output_event）。"""
    if event_key in EVENT_PRODUCERS:
        return True
    for s in SERVICES.values():
        if isinstance(s, dict) and s.get("output_event") == event_key:
            return True
    return False


# ══════════════════════════════════════════════════════════════════════════
# S1 正常波次：意图 → 交付 → 发布 → 交接 → 销毁（全相位走查）
# ══════════════════════════════════════════════════════════════════════════
def scenario_happy_path():
    name = "S1-happy-path"
    log(name, "意图: '给 template-service 加 /healthz 端点'")
    team = TEAMS.get("dev-wave") or {}
    check(bool(team), "A1", "S1: registry 无 delivery_squad 实例（dev-wave）——团队无法实例化")

    # ① 意图入境（机制）→ 组队（trigger）→ owner 批验收示例
    check(event_has_producer("intent.received"), "A5", "S1: intent.received 无生产者（冷启动断——组队事件悬空）")
    trig = str((team.get("lifecycle") or {}).get("trigger", ""))
    check("intent.received" in trig, "A1",
          f"S1: delivery_squad 实例 trigger 应为 intent.received（实={trig}——intent.ratified 组队会让 planner 产示例时无所属团队/预算无池）")
    bucket = owner_blocking_registered("intent_ratification")
    check(bucket == "synchronous", "A3",
          f"S1: intent_ratification 应为 synchronous（实={bucket}——验收示例批准不可异步默认）")

    # ② planner 产卡（plan 相位在场？能写 contracts？退场条件可求值？）
    check(seat_present("planner", "plan"), "A1", "S1: planner 不在 plan 相位在场表")
    p_agent = seat_agent("planner", team)
    check(p_agent is not None, "A1", "S1: delivery_squad 实例缺 planner 座位 agent")
    planner_seat = SEAT_PHASES.get("planner") or {}
    check("cards.ratified" in str(planner_seat.get("exit_on", "")), "A6",
          "S1: planner 无 exit_on（plan→build 边条件 planner.state==exited 不可求值——主流程死锁）")
    wc = (TEAMS_STD.get("delivery_squad") or {}).get("wave_consistency") or {}
    contracts_ok = "contracts" in str((PROFILES.get("planner") or {}).get("duty_assurance", {})
                                      .get("structural", [{}])[0].get("claim", ""))
    p_overrides = str((AGENTS.get(p_agent) or {}).get("permissions", {}).get("overrides", ""))
    check(contracts_ok and "contracts" in p_overrides, "A2",
          "S1: planner 写路径不含 contracts/（profile 白名单或实例 deny pattern 缺——N>1 时跨卡契约产不出 → 死锁）")
    log(name, f"planner({p_agent}) 产卡 ×3 + contracts/<wave_id>.yaml + 验收示例")

    # ③ test_author plan 相位可测性审查 + 冻结测试树
    check(seat_present("test_author", "plan"), "A1", "S1: test_author 不在 plan 相位（可测性审查缺位）")
    ta_agent = seat_agent("test_author", team)
    check(ta_agent is not None, "A1", "S1: 实例缺 test_author 座位")
    ta_member = next((m for m in team.get("members", []) if m.get("seat") == "test_author"), {})
    check(not ta_member.get("as_tool", False), "A1",
          "S1: test_author 以 as_tool 绑定（单次往返装不下 verify→build→verify 多轮 review 回路——应实体座位）")
    log(name, f"test_author({ta_agent}) 逐卡 testability_signoff + test_tree_sha 冻结")

    # ④ card_gate 机制批准 → cards.ratified
    gate = SERVICES.get("card_gate") or {}
    check(gate.get("output_event") == "cards.ratified", "A5", "S1: card_gate 未声明 output_event=cards.ratified")
    req = str(gate.get("requires", []))
    check("testability_signoff" in req, "A5", "S1: card_gate.requires 缺 testability_signoff")
    check("test_tree_sha" in req or "冻结" in req, "A5",
          "S1: card_gate.requires 缺测试树冻结（cards.ratified 可在验收树缺失时发生）")
    check(str(gate.get("owner_involvement")) == "none", "A3", "S1: card_gate 有 owner 参与（应为纯机制）")
    log(name, "card_gate 全绿 → cards.ratified（机制输出，owner_involvement=none）")

    # ⑤ 相位转移 plan→build
    e = phase_edge_ok("plan", "cards.ratified")
    check(e is not None, "A6", "S1: 相位图无 plan→build 边（事件 cards.ratified）")
    check("planner.state == exited" in str(e and e.get("when")), "A6", "S1: plan→build 边缺 planner 退场条件（竞态）")
    log(name, "planner 退场（exit_on: cards.ratified）；相位 plan→build")

    # ⑥ builder 实现卡（权限 + 预算按 risk_class）
    check(seat_present("builder", "build"), "A1", "S1: builder 不在 build 相位")
    b_agent = seat_agent("builder", team)
    check(b_agent is not None, "A1", "S1: 实例缺 builder 座位")
    check("fs_write_repo" in agent_allow("builder", b_agent), "A2",
          f"S1: builder({b_agent}) allow 缺 fs_write_repo（无法写实现）")
    per_card = str((team.get("budget") or {}).get("per_card", ""))
    check("risk_class" in per_card, "A4",
          f"S1: 团队 per_card 预算未声明按 risk_class（实='{per_card}'——全局常量预算=三层漂移）")
    log(name, f"builder({b_agent}) 按卡实现（budget=per_card 按 risk_class，retries 同）")

    # ⑦ researcher as_tool 检索（overhead_pool——对 builder 免费）
    r_agent = seat_agent("researcher", team)
    if r_agent:
        log(name, f"researcher({r_agent}) as_tool 检索（overhead_pool 承担）")
        check("overhead_pool" in str(team.get("budget") or {}), "A4",
              "S1: 团队声明缺 overhead_pool（检索计入 builder 卡预算——惩罚诚实）")

    # ⑧ builder 提 PR → verify
    check(phase_edge_ok("build", "pr.opened") is not None, "A6", "S1: 相位图无 build→verify 边（pr.opened）")
    log(name, "builder 提 PR（附卡号+验收引用）→ 相位 verify")

    # ⑨ verifier 判卷（gate 层机制）+ test_author review
    check(seat_present("test_author", "verify"), "A1", "S1: test_author 不在 verify 相位（review 无人做）")
    check(seat_present("builder", "verify"), "A1", "S1: builder 不在 verify 相位（review 驳回后无法返工）")
    vl = (TC.get("flow") or {}).get("verdict_layers") or {}
    check(str((vl.get("gate") or {}).get("type")) == "mechanism", "A2", "S1: gate 层非机制")
    check("seat(test_author)" in str((vl.get("review") or {}).get("type", "")), "A1",
          "S1: review 层非 test_author 座位（意图符合性审查缺位）")
    # review 裁定的发布面（合并闸门钥匙之一——无频道=verify 永远出不去）
    acl = (((TC.get("channels") or {}).get("pub_sub") or {}).get("acl") or {})
    review_acl = acl.get("review.*") or {}
    check("test_author" in (review_acl.get("write") or []), "A7",
          "S1: review.* 频道缺失或不允许 test_author 写（review.approve 有生产者无发布面——合并闸门死锁）")
    log(name, "verifier 跑冻结树（gate 层）+ test_author review（review.* 频道发布）→ pass")

    # ⑩ 合并 → integrate
    e = phase_edge_ok("verify", "gate.pass")
    check(e is not None and "integrate" in str(e and e.get("to")), "A6",
          "S1: 相位图无 verify→integrate 边（gate.pass AND review.approve）")
    check("integrator" in str((TC.get("flow") or {}).get("merge_policy", "")), "A2", "S1: merge_policy 缺 integrator 机制")
    log(name, "integrator 自动合并（gate.pass AND review.approve）")

    # ⑪ release_bot 部署 behind flag + release_record
    check(bool(SERVICES.get("release_bot")), "A1", "S1: 缺 release_bot 服务（发布无执行者）")
    rr = (TC.get("artifacts") or {}).get("release_record") or {}
    check("rollback_safe" in (rr.get("fields") or []), "A5", "S1: release_record 缺 rollback_safe 字段")
    check(event_has_producer("released_behind_flag"), "A5", "S1: released_behind_flag 无生产者")
    log(name, "release_bot 部署 behind flag → release_record(rollback_safe=true) → released_behind_flag")

    # ⑫ integrate→handoff → 交接 → 销毁
    e = phase_edge_ok("integrate", "released_behind_flag")
    check(e is not None and "handoff" in str(e and e.get("to")), "A6",
          "S1: 相位图无 integrate→handoff 边（发布后无相位表达——release 停滞时状态机不可见）")
    check(seat_present("test_author", "handoff"), "A1", "S1: test_author 不在 handoff 相位（retrospective 无执行者）")
    life = (TEAMS_STD.get("delivery_squad") or {}).get("lifecycle") or {}
    ho = life.get("handoff") or {}
    team_side = ho.get("team_side") or []
    check(bool(team_side), "A1", "S1: delivery_squad.handoff.team_side 为空（交接无清单）")
    for item in team_side:
        check(bool(item.get("by")), "A1", f"S1: handoff 项 {item.get('item')} 无执行者（队永不销毁——ephemeral 死锁）")
    check(bool(ho.get("stewardship_side")), "A1", "S1: handoff 无 stewardship_side（memory-distill/adr-write 无消费侧）")
    log(name, "handoff(team_side 逐项有主) → stewardship 异步消费(归档资产) → destroy(after-handoff AND released)")
    check((TEAMS.get("stewardship") or {}).get("lifecycle", {}).get("type") == "persistent", "A1",
          "S1: stewardship 实例缺失或非 persistent（归档目标不存在——跨生命周期接口断裂）")
    log(name, "PASS-END")


# ══════════════════════════════════════════════════════════════════════════
# S2 normative amendment 超时——默认动作必须是冻结而非 approve
# ══════════════════════════════════════════════════════════════════════════
def scenario_amendment_timeout():
    name = "S2-amendment-timeout"
    log(name, "builder 发现卡歧义 → amendment_request(normative) → owner 未响应 24h")
    amend = (((((TC.get("artifacts") or {}).get("card") or {}).get("lifecycle") or {})
              .get("amendment") or {}).get("classify") or {}).get("normative") or {}
    d = str(amend.get("default_on_timeout_24h", ""))
    check(("冻结" in d) and ("绝不 approve" in d or "approve" not in d), "A3",
          f"S2: normative amendment 超时默认动作不安全（实='{d}'——默认 approve = spec gaming 门）")
    bucket = owner_blocking_registered("normative_amendment_daily")
    check(bucket in ("asynchronous", "sampled"), "A3", "S2: normative_amendment 不在注意力账本（悬空阻塞点）")
    during = ((((TC.get("artifacts") or {}).get("card") or {}).get("lifecycle") or {})
              .get("amendment") or {}).get("during") or {}
    check(during.get("budget_clock") == "paused", "A4", "S2: amendment 期间预算时钟未暂停（惩罚提出歧义的诚实方）")
    e = phase_edge_ok("any", "amendment.normative.accepted")
    check(e is not None and e.get("to") == "plan", "A6", "S2: 相位图无 any→plan 重入边（planner 无法重入修卡）")
    # amendment_request 是制品（有 schema 可校验）
    ar = (TC.get("artifacts") or {}).get("amendment_request") or {}
    check(bool(ar.get("fields")), "A5", "S2: amendment_request 无字段定义（'artifact 非消息'沦为口号）")
    check((REG / "schemas" / "amendment-request.json").exists(), "A5",
          "S2: registry/schemas/amendment-request.json 缺失（amendment_request 无 schema）")
    log(name, "默认动作=卡冻结+退回 backlog+波次继续其余卡；budget_clock paused；planner 重入可行")


# ══════════════════════════════════════════════════════════════════════════
# S3 sev1 事故，rollback_safe=false——半夜不毁数据（授权矩阵对齐词表+responder.allow）
# ══════════════════════════════════════════════════════════════════════════
def scenario_incident_unsafe_rollback():
    name = "S3-incident-unsafe-rollback"
    log(name, "sev1 告警 + release_record.rollback_safe=false + owner 睡觉")
    ic = TEAMS_STD.get("incident_cell") or {}
    auth = ic.get("authorization") or {}
    sev1 = auth.get("sev1") or {}
    resp_allow = agent_allow("responder")
    then_actions = sev1.get("actions_then") or []
    else_actions = sev1.get("actions_else") or []
    check("deploy_reverse" in then_actions, "A2", "S3: sev1 安全窗内无 deploy_reverse（预授权失效）")
    check("deploy_reverse" not in else_actions, "A2", "S3: sev1 不安全时 deploy_reverse 仍预授权（半夜毁数据）")
    check("data_freeze" in else_actions, "A2", "S3: 不安全时缺 data_freeze（停止流血动作缺失）")
    # A2 深检：授权动作必须落在词表内且 ⊆ responder.allow（否则授权矩阵=纸面授权，执行层过不去）
    for label, actions in (("sev1.then", then_actions), ("sev1.else", else_actions),
                           ("sev1_di.pre", (auth.get("sev1_data_integrity") or {}).get("preauthorized") or []),
                           ("sev2.then", ((auth.get("sev2") or {}).get("actions_then")) or [])):
        for a in actions:
            check(a in VOCAB, "A2", f"S3: 授权动作 {a}（{label}）不在 side-effects 词表（不可执行/不可校验）")
            check(a in resp_allow, "A2",
                  f"S3: 授权动作 {a}（{label}）不在 responder capabilities.allow（授权矩阵与白名单矛盾——事故持续到 owner 醒）")
    check("rollback_safe" in str(sev1.get("preauthorized_if", "")), "A5", "S3: sev1 预授权条件未引用 rollback_safe")
    sev2 = auth.get("sev2") or {}
    check("rollback_safe" in str(sev2.get("deploy_reverse", "")), "A2",
          "S3: sev2 deploy_reverse 未受 rollback_safe 约束（超时自动放行不安全回滚）")
    di = auth.get("sev1_data_integrity") or {}
    check("deploy_reverse" in (di.get("forbidden_without_owner") or []), "A2",
          "S3: 数据完整性事故未禁 deploy_reverse（回滚=加害动作）")
    life = ic.get("lifecycle") or {}
    check("escalate" in str(life.get("on_ttl_expiry", "")), "A5", "S3: TTL 到期未升级 owner（auto-destroy=事故静默消失）")
    exit_c = life.get("exit_criteria") or {}
    check("followup_cards_created" in (exit_c.get("requires") or []), "A5",
          "S3: 事故退出条件缺 followup_cards_created（修复停留在 retro 文档）")
    check("owner" not in (ic.get("seats") or {}) and "responder" in (ic.get("seats") or {}), "A1",
          "S3: owner 混入 seats（principals 应分列）或 responder 缺失")
    # sev2 ack 在账本（15m 级响应若不入账=击穿注意力预算）
    check(owner_blocking_registered("sev2_rollback_ack") is not None, "A3",
          "S3: sev2_rollback_ack 不在注意力账本（悬空阻塞点）")
    log(name, "不安全窗: flag/failover/scale/data_freeze 预授权且 ⊆ responder.allow；deploy_reverse 降级；TTL 升级")


# ══════════════════════════════════════════════════════════════════════════
# S4 升级预算耗尽——升级通道不被掐断
# ══════════════════════════════════════════════════════════════════════════
def scenario_escalation_budget():
    name = "S4-escalation-budget"
    log(name, "builder↔test_author 僵持 + overhead_pool 已耗尽")
    inv = (TC.get("budget") or {}).get("invariants") or []
    check(any("永不受任何预算约束" in str(i) for i in inv), "A4",
          "S4: 预算不变式缺'升级通道永不冻结'（预算可封口升级——静默合谋温床）")
    esc = ((TC.get("paradigms") or {}).get("handoff") or {}).get("subtype escalation") or {}
    check(bool(esc), "A1", "S4: handoff 缺 escalation 子类型")
    arb = ((TC.get("flow") or {}).get("verdict_layers") or {}).get("arbitration") or {}
    dd = arb.get("during_dispute") or {}
    check(dd.get("run") == "frozen", "A1", "S4: 争议期间卡状态未定义（during_dispute 缺 run:frozen）")
    check(owner_blocking_registered("dispute_escalation_before_judge") is not None, "A3",
          "S4: judge 激活前僵持直达 owner 不在账本（公理'一切阻塞点入账本'违反）")
    log(name, "僵持 → 卡冻结+escalation 直达 owner（judge 未激活）；预算耗尽本身即 escalation 事件")


# ══════════════════════════════════════════════════════════════════════════
# S5 judge 激活前缺席——路由不悬空；激活后实例可用（族独立+approved）
# ══════════════════════════════════════════════════════════════════════════
def scenario_judge_not_activated():
    name = "S5-judge-activation"
    log(name, "僵持首次发生（judge_service 未触发：累计<2）→ 激活（累计>=2）→ 实例化")
    arb = ((TC.get("flow") or {}).get("verdict_layers") or {}).get("arbitration") or {}
    check("直达 owner" in str(arb.get("routing", "")), "A1", "S5: judge 未激活时仲裁路由未回退 owner（悬空）")
    jt = (ACT.get("on_trigger") or {}).get("judge_service") or {}
    check("僵持累计 >= 2" in str(jt.get("when", "")), "A5", "S5: judge 激活条件缺机器可判定事件")
    jsvc = SERVICES.get("judge") or {}
    # 激活时实例真的能建起来：成员 approved + 族独立于争议双方
    for m in (jsvc.get("members") or []):
        aid = str(m).removeprefix("agent:")
        ag = AGENTS.get(aid) or {}
        check(ag.get("status") == "approved", "A1",
              f"S5: judge 成员 {aid} status={ag.get('status')}（非 approved 无法按 AGENTS.md 组建）")
        fam = (MODELS.get((ag.get("model") or {}).get("alias")) or {}).get("family")
        for other_arch in ("builder", "test-author"):
            for oid, oag in AGENTS.items():
                if oag.get("archetype") == other_arch:
                    ofam = (MODELS.get((oag.get("model") or {}).get("alias")) or {}).get("family")
                    check(fam != ofam, "A2",
                          f"S5: judge({aid}:{fam}) 与 {other_arch}({oid}:{ofam}) 同族（族独立性被实例违反——validate 全局比对同查）")
    # 判官无写路径（CT-JDG-001）但判决有产出通道
    check(agent_allow("judge").isdisjoint({"datastore_write", "fs_write_repo", "fs_write_sandbox"}), "A2",
          "S5: judge allow 含写路径（CT-JDG-001 判决不可污染声明为假）")
    check(not (jsvc.get("writes") or []), "A5",
          "S5: services.judge.writes 非空但 judge 无写能力（声明矛盾——写权应=平台自述通道+curator 入库）")
    log(name, "路由=直达 owner；激活=僵持累计>=2；实例=approved+异族+无写路径；判决经平台自述事件")


# ══════════════════════════════════════════════════════════════════════════
# S6 sev3 边界 + 事故单元可实例化（A1：实例与座位绑定真实存在）
# ══════════════════════════════════════════════════════════════════════════
def scenario_incident_instantiation():
    name = "S6-incident-instantiation"
    log(name, "sev3 走常规卡；sev1/sev2 事故单元实例化（座位绑定可用）")
    ic_std = TEAMS_STD.get("incident_cell") or {}
    check("sev3" not in (ic_std.get("severity_bound") or []) and "sev1" in (ic_std.get("severity_bound") or []),
          "A2", "S6: severity_bound 错误（sev3 应走 delivery 常规卡）")
    team = TEAMS.get("incident-cell") or {}
    check(bool(team), "A1",
          "S6: registry 无 incident_cell 实例（声明了 seats/授权矩阵却无可绑定 agent——sev1 到来时无法实例化）")
    if team:
        for seat in ("responder", "deployer"):
            aid = seat_agent(seat, team)
            check(aid is not None, "A1", f"S6: incident-cell 实例缺 {seat} 座位 agent")
            if aid:
                check(AGENTS.get(aid, {}).get("status") == "approved", "A1",
                      f"S6: {seat} 实例 {aid} 非 approved（事故来临无法组建）")
                check(archetype_of(seat) == AGENTS.get(aid, {}).get("archetype"), "A1",
                      f"S6: {seat} 座位绑定了错误原型的 agent:{aid}")
        check((team.get("lifecycle") or {}).get("archive_to", "").endswith("stewardship"), "A1",
              "S6: incident-cell archive_to 非 stewardship（retro 债无追踪方）")
    log(name, "sev3 → delivery 常规卡；incident-cell 实例就绪（responder/deployer approved 绑定）")


# ══════════════════════════════════════════════════════════════════════════
# S7 backlog 回路——治理产出必须被消费（生产/消费双强制点）
# ══════════════════════════════════════════════════════════════════════════
def scenario_backlog_loop():
    name = "S7-backlog-loop"
    log(name, "escape review 产 backlog 提案 → curator 归并 → 下波次 planner 必须处置")
    bl = (TC.get("interfaces") or {}).get("backlog") or {}
    check(bool(bl.get("producer_gate")), "A5", "S7: backlog 无 producer_gate（治理→交付回路断）")
    card = (TC.get("artifacts") or {}).get("card") or {}
    kr = card.get("knowledge_refs") or {}
    check("forbidden" in kr, "A5", "S7: card.knowledge_refs 无 forbidden 自证不存在（强制点退化成仪式）")
    fields = card.get("fields_required") or []
    check(any("applies_adr" in str(f) for f in fields), "A5", "S7: card 字段缺 applies_adr（消费侧强制点缺失）")
    # escape 事件生产者（escape_found 有主才有指标数据源）
    check(event_has_producer("escape_found"), "A5", "S7: escape_found 无生产者（escape_rate 指标失去数据源）")
    esc = (FLOWS.get("escape_review") or {}).get("steps") or {}
    check("backlog" in str(esc.get(2, "")), "A5",
          "S7: escape_review 未产 backlog 提案（原队已销毁时回归测试无执行者——回路断在时序上）")
    log(name, "escape→backlog 提案（含回归测试卡）→ curator 归并 → 下波次 producer_gate 强制处置")


# ══════════════════════════════════════════════════════════════════════════
# S8 gaming 检测——holdout 首开不循环依赖；tests/acceptance 规则不淹没通道
# ══════════════════════════════════════════════════════════════════════════
def scenario_gaming_detection():
    name = "S8-gaming-detection"
    log(name, "builder PR 触及 tests/acceptance/**；holdout 失败但 visible 全绿（holdout 未激活→激活）")
    ta = (TC.get("artifacts") or {}).get("test_assets") or {}
    rules = str(ta.get("hard_rules", []))
    check("tests/acceptance" in rules, "A2",
          "S8: hard_rules 未区分 tests/acceptance 与 tests/unit（builder 必写 unit——不区分则规则形同虚设或通道被噪音淹没）")
    holdout = ta.get("holdout_suite") or {}
    act_when = str((ACT.get("on_trigger") or {}).get("holdout_suite", {}).get("when", ""))
    non_circular = ("risk_class" in act_when) or ("change_class" in act_when)
    check(non_circular, "A3",
          "S8: holdout 激活条件只含 gaming 唯一信号源=holdout 自身（循环依赖——首个 logic 卡永远无 gaming 检测）")
    for cc in _extract_classes(act_when):
        check(cc in (CHANGECLASSES.get("classes") or {}), "A5",
              f"S8: holdout 激活条件引用不存在的 change_class '{cc}'（机器不可判定）")
    log(name, "首开杠杆=risk_class=high 或 change_class∈[schema,dep]（非循环）；acceptance 触碰强制 test_author review")


def _extract_classes(s):
    import re
    inner = re.search(r"∈\s*\[([^\]]+)\]", s)
    return [c.strip() for c in inner.group(1).split(",")] if inner else []


# ══════════════════════════════════════════════════════════════════════════
# S9 "测试写错了"修复路径——amendment.test_fix 可达，不依赖 planner 重入
# ══════════════════════════════════════════════════════════════════════════
def scenario_test_fix_path():
    name = "S9-test-fix-path"
    log(name, "builder 主张'测试写错了' → amendment_request(test_fix) → test_author 修正（非减弱型 auto）")
    cls = ((((TC.get("artifacts") or {}).get("card") or {}).get("lifecycle") or {})
           .get("amendment") or {}).get("classify") or {}
    tf = cls.get("test_fix") or {}
    check(bool(tf), "A1",
          "S9: amendment.classify 无 test_fix 类（'测试写错了'修复路径不可达——判决执行断裂在判决之前）")
    if tf:
        check("test_author" in str(tf.get("initiator", "")), "A1", "S9: test_fix 的 initiator 非 test_author")
        check(str(tf.get("apply")) == "auto", "A3", "S9: test_fix 非 auto（非减弱型修正无需 owner 日批）")
        check("减弱" in str(tf.get("guard", "")), "A2", "S9: test_fix 无减弱型护栏（删测试/放宽断言可借此通道偷渡）")
    nn = cls.get("non_normative") or {}
    check("planner" not in str(nn.get("reviewer", "")), "A6",
          "S9: non_normative reviewer 含 planner 重入但相位图无边（悬空路径）")
    log(name, "test_fix(auto+减弱护栏) 可达；减弱型走特权变更（owner 批+test_weakening 事件）")


# ══════════════════════════════════════════════════════════════════════════
# S10 冷启动 + 事件完备性（A7）——状态机引用的一切事件有生产者
# ══════════════════════════════════════════════════════════════════════════
def scenario_event_completeness():
    name = "S10-event-completeness"
    log(name, "遍历相位图事件 + 关键流事件 → 逐一断言有生产者（A7）")
    import re
    checked = set()
    for e in GRAPH:
        when = str(e.get("when", ""))
        for tok in re.split(r"AND|OR|\s+", when):
            tok = tok.strip("() ")
            if "." in tok and tok[0].islower() and not tok.startswith(("planner", "builder")):
                checked.add(tok)
    for ev in sorted(checked):
        check(event_has_producer(ev), "A7", f"S10: 相位边事件 '{ev}' 无生产者（悬空事件=状态机不可执行）")
    for ev in ("escape_found", "test_weakening", "verdict_stalemate", "released_behind_flag", "reverted",
               "pr.merged", "wave.frozen", "incident.sev_alert"):
        check(event_has_producer(ev), "A7", f"S10: 关键流事件 '{ev}' 无生产者")
    log(name, f"相位图+关键流共 {len(checked) + 8} 个事件全部有生产者；trace_id 由信封强制贯穿（channels.routed_a2a）")


# ══════════════════════════════════════════════════════════════════════════
# S11 信任链完整性——io_contract schema 存在；机制服务有原型（词表 fail-closed 全覆盖）
# ══════════════════════════════════════════════════════════════════════════
def scenario_trust_chain():
    name = "S11-trust-chain"
    log(name, "io_contract schema 实存；services 机制有原型注册（信任声明不缺位）")
    missing = []
    for aid, a in AGENTS.items():
        for side in ("input", "output"):
            sr = ((a.get("io_contract") or {}).get(side) or {}).get("schema_ref")
            if sr and not (REG / sr).is_file():
                missing.append(f"{aid}:{sr}")
    check(not missing, "A7", f"S11: io_contract.schema_ref 悬空: {missing[:5]}（输出 schema 是信任机制地基）")
    mech_names = {k for k, v in PROFILES.items() if isinstance(v, dict) and v.get("kind") == "mechanism"}
    for svc in ("card_gate", "release_bot", "knowledge_retrieval", "drift_check"):
        proto = {"card_gate": "card-gate", "release_bot": "release-bot",
                 "knowledge_retrieval": "knowledge-retrieval", "drift_check": "drift-check"}.get(svc)
        check(proto in mech_names, "A1",
              f"S11: services.{svc} 无机制原型注册（持权服务无 capabilities/信任声明——词表 fail-closed 制度漏洞）")
        allow = ((PROFILES.get(proto) or {}).get("capabilities") or {}).get("allow") or []
        bad = set(allow) - VOCAB
        check(not bad, "A2", f"S11: 机制原型 {proto} allow 含词表外副作用 {sorted(bad)}")
    # schema 语义抽查（存在≠正确——关键闸门的 schema 必须真强制）
    import json as _json
    fnd = _json.loads((REG / "schemas" / "findings.json").read_text(encoding="utf-8"))
    check((fnd.get("properties", {}).get("sources", {}) or {}).get("minItems") == 1, "A2",
          "S11: findings.json sources 无 minItems:1（'无引用结论无法通过输出校验'=假声明，CT-RES-002 落空）")
    inc = _json.loads((REG / "schemas" / "incident-in.json").read_text(encoding="utf-8"))
    check("sev3" not in (inc.get("properties", {}).get("severity", {}) or {}).get("enum", []), "A2",
          "S11: incident-in.json severity 含 sev3（severity_bound 分流后不应入境——误投时行为未定义）")
    vr = _json.loads((REG / "schemas" / "verdict.json").read_text(encoding="utf-8"))
    check("case_law_dispositions" in (vr.get("required") or []), "A2",
          "S11: verdict.json 不强制 case_law_dispositions（'禁自证无相关判例'在 schema 层不可判）")
    log(name, "全部 io_contract schema 实存；4 个服务机制均有原型+词表内 allow；关键 schema 语义强制抽查通过")


# ══════════════════════════════════════════════════════════════════════════
# S12 跨生命周期——ephemeral 销毁后 stewardship 消费（无销毁依赖）
# ══════════════════════════════════════════════════════════════════════════
def scenario_cross_lifecycle():
    name = "S12-cross-lifecycle"
    log(name, "dev-wave 销毁后 stewardship 消费 handoff 资产（原队 agent 已不存在）")
    life = (TEAMS_STD.get("delivery_squad") or {}).get("lifecycle") or {}
    ss = life.get("handoff", {}).get("stewardship_side") or []
    check("memory-distill" in ss and "adr-write" in ss, "A1",
          "S12: stewardship_side 缺 memory-distill/adr-write（队销毁后知识沉淀无消费方）")
    # 消费侧不依赖原队存活成员的私有记忆：curator 能力覆盖消费动作
    cur_allow = agent_allow("curator")
    check("datastore_read" in cur_allow and "fs_write_repo" in cur_allow, "A2",
          "S12: curator allow 不足以消费归档资产（读归档/写 ADR）")
    # 数据层制品不随队销毁（destroy_scope 声明）
    check("数据层" in str(life.get("destroy_scope", "")), "A5",
          "S12: destroy_scope 未声明数据层制品保留（销毁语义模糊——资产可能随队丢失）")
    # 交接物有 schema（handoff-in）
    check((REG / "schemas" / "handoff-in.json").exists(), "A5", "S12: schemas/handoff-in.json 缺失（交接无契约）")
    log(name, "销毁→归档资产（事件流/PR）留存→curator 异步蒸馏入库；无对已销毁 agent 的活引用")


def run():
    scenarios = (scenario_happy_path, scenario_amendment_timeout, scenario_incident_unsafe_rollback,
                 scenario_escalation_budget, scenario_judge_not_activated, scenario_incident_instantiation,
                 scenario_backlog_loop, scenario_gaming_detection, scenario_test_fix_path,
                 scenario_event_completeness, scenario_trust_chain, scenario_cross_lifecycle)
    for fn in scenarios:
        trace.append(f"── {fn.__name__} " + "─" * 40)
        fn()
    print("\n".join(trace))
    print("─" * 72)
    if errors:
        print(f"SIMULATION FAIL ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print(f"SIMULATION OK: {len(scenarios)} 场景全通（happy-path/amendment/unsafe-rollback/escalation-budget/"
          "judge-activation/incident-instantiation/backlog-loop/gaming/test-fix/event-completeness/"
          "trust-chain/cross-lifecycle）")


if __name__ == "__main__":
    run()
