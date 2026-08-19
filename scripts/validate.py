#!/usr/bin/env python3
"""registry 声明校验 v2（ADR-0010）：词表白名单 + profile 一致性 + 族级独立性 + CT 覆盖率。

v2 要点（对照 v1）：
  - 白名单制（fail-closed）：capabilities.allow ⊆ side-effects.yaml v2 词表；
    agent 工具副作用 ⊆ allow（组合规则）
  - agent_tools {refs} 对照 profile {allow(原型), max}——v1 黑名单废弃
  - isolation/approval/trust_zone 必须与 profile 一致（v1 permissions.mode 双义拆分）
  - 独立性升级为族级（models.yaml family；v1 别名级太弱）
  - profiles 每条 structural 必须有 claim/enforced_by/control_test，且 CT 在
    control-tests.yaml 登记（ct-coverage，CT-ADV-003）
  - team 验收结构 v2：test_authors（LLM 出题）+ verdict_by=mechanism:verifier（判卷）
  - REGISTRY_DATA_ROOT 环境变量：CI 用 base ref 的校验器审 head 的数据（自指门禁修复）

退出码非 0 = CI 拒绝。对应 GOVERNANCE AR-2 / AR-6。
"""
import json
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent          # 标准侧（校验器+profiles+词表；CI 中来自 base ref）
DATA = Path(os.environ.get("REGISTRY_DATA_ROOT", ROOT))  # 数据侧（registry 数据；CI 中来自 PR head）
REG = DATA / "registry"
errors = []


def fail(msg: str) -> None:
    errors.append(msg)


def dig(d, path: str):
    """按点路径取值；任一层非 dict 即返回 None"""
    cur = d
    for k in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def load_yaml(path: Path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:  # noqa: BLE001
        fail(f"YAML 解析失败: {path}: {e}")
        return None


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        fail(f"缺少 frontmatter: {path}")
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except Exception as e:  # noqa: BLE001
        fail(f"frontmatter 解析失败: {path}: {e}")
        return {}


# ---- 加载：数据侧 ----
tools = {p.stem: load_yaml(p) or {} for p in (REG / "tools").glob("*.yaml")}
agents = {p.stem: load_yaml(p) or {} for p in (REG / "agents").glob("*.yaml")}
teams = {p.stem: load_yaml(p) or {} for p in (REG / "teams").glob("*.yaml")}
skills = {p.parent.name: frontmatter(p) for p in (REG / "skills").glob("*/SKILL.md")}
models = (load_yaml(REG / "models.yaml") or {}).get("models", [])
model_aliases = {m.get("alias") for m in models}
model_family = {m.get("alias"): m.get("family") for m in models}

# ---- 加载：标准侧（始终随校验器，CI 中 = base ref）----
PROFILES = (load_yaml(ROOT / "standards" / "archetype-profiles.yaml") or {}).get("profiles", {})
VOCAB = set()
_se = load_yaml(ROOT / "standards" / "side-effects.yaml") or {}
for _grp in (_se.get("groups") or {}).values():
    VOCAB.update(_grp.keys())
# ── 执行通道词表（ADR-0022——issue #31 收敛判据 9）：每个副作用词必居一通道 ──
_dc = (_se.get("delivery_channels") or {})
_TOOL_REQ = set(_dc.get("tool_required") or [])
_ALL_CHANNELS = _TOOL_REQ | set(_dc.get("platform_direct") or []) | set(_dc.get("runtime_builtin") or [])
_unchanneled = VOCAB - _ALL_CHANNELS
if _unchanneled:
    fail(f"side-effects: delivery_channels 未覆盖词表 {sorted(_unchanneled)}（词无通道=执行面不可判，ADR-0022）")
CT_REG = (load_yaml(ROOT / "standards" / "control-tests.yaml") or {}).get("tests", {})
# checks 注册表提前加载（ADR-0022：must_run 的 check: 引用校验需要 id 集）；
# 根类型校验（评审项）：列表/标量根须报结构错误而非崩溃
CHECKS_REG = load_yaml(ROOT / "standards" / "checks.yaml") or {}
if not isinstance(CHECKS_REG, dict):
    fail(f"checks.yaml 根节点须为对象（version/checks），实为 {type(CHECKS_REG).__name__}")
    CHECKS_REG = {}
elif not isinstance(CHECKS_REG.get("checks"), list):
    fail(f"checks.yaml 的 checks 须为列表，实为 {type(CHECKS_REG.get('checks')).__name__}")
    CHECKS_REG["checks"] = []
_CHECKS_LOADED = {_c.get("id") for _c in CHECKS_REG.get("checks", []) or [] if isinstance(_c, dict)}
# 标准文件可解析性（flows/change-classes 暂无结构校验，先保证解析不失败——CodeRabbit #5）
for _std in ("flows.yaml", "change-classes.yaml", "team-collaboration.yaml", "attention-ledger.yaml"):
    if (load_yaml(ROOT / "standards" / _std) or {}) == {}:
        fail(f"standards/{_std} 缺失或解析为空（标准文件必须可解析，ADR-0010）")

# attention-ledger 断言（team-collaboration v1.0：conservation_rule 的硬表达）
# ADR-0022（issue #31 D-4）：守恒的是【类目数】——键名 max_synchronous_categories；
# 每周实际频次由类目语义界定并在 metrics 周报可审计（运行时数据，静态层不伪校验）
_LEDGER = load_yaml(ROOT / "standards" / "attention-ledger.yaml") or {}
_sync = _LEDGER.get("synchronous") or []
_max = _LEDGER.get("max_synchronous_categories")
if _max is None and _LEDGER.get("max_synchronous_per_week") is not None:
    fail("attention-ledger: max_synchronous_per_week 已更名 max_synchronous_categories"
         "（静态层守恒类目数——ADR-0022 语义对齐 issue #31 D-4）")
if _max is not None and len(_sync) > _max:
    fail(f"attention-ledger: synchronous 阻塞类目 {len(_sync)} 个 > 上限 {_max}（conservation_rule 违反——新增必须移除一个）")
for _entry in _sync:
    if isinstance(_entry, dict) and not (_entry.get("default") or _entry.get("why_blocking")):
        fail(f"attention-ledger: synchronous 项 {_entry.get('item')} 缺 default 且缺 why_blocking（人在环点必须有确定行为或不可默认理由）")
for _entry in _LEDGER.get("asynchronous") or []:
    if isinstance(_entry, dict) and not any(str(_k).startswith("default") for _k in _entry):
        fail(f"attention-ledger: asynchronous 项 {_entry.get('item')} 缺 default/default_Nh（无默认动作=owner 缺席时状态未定义）")

# team-collaboration v1.0 结构断言：相位图无死锁（每 phase 有出边或为终态）
_TC = load_yaml(ROOT / "standards" / "team-collaboration.yaml") or {}
_graph = ((_TC.get("flow") or {}).get("phases") or {}).get("graph") or []
_order = ((_TC.get("flow") or {}).get("phases") or {}).get("phase_order") or []
if _graph and _order:
    _terminal = {"handoff"}   # 终态（波次出口；队销毁由 lifecycle.destroy 表达）
    for _ph in _order:
        if _ph in _terminal:
            continue
        # ADR-0022（issue #31 A-4）：any 通配边不计为具体相位的出边——旧实现
        # `str(e.get("from")) in (_ph, "any")` 因永久存在的 any 边而对任意相位恒真
        if not any(str(e.get("from")) == _ph and e.get("when") is not None for e in _graph):
            fail(f"team-collaboration: phase '{_ph}' 无专属出边（死锁相位——any 通配边不计，ADR-0022）")

# 相位图事件的生产者完整性（flow.event_producers——悬空事件=状态机不可执行）
_evt_prod = (_TC.get("flow") or {}).get("event_producers") or {}
for _e in _graph:
    for _tok in str(_e.get("when", "")).replace("AND", " ").replace("OR", " ").split():
        _k = _tok.strip("() \t")            # ADR-0022：剥离括号（OR 分支的 "(review.approve" 形态）
        if _k and "." in _k and _k not in _evt_prod and not _k.startswith(("planner", "builder", "wave")):
            fail(f"team-collaboration: 相位边事件 '{_k}' 无生产者（flow.event_producers 缺项）")

# ── 生产者引用解析（ADR-0022：issue #31 变异 F——seat:/agent: 悬空引用灭绝）──
_SEATS_DEF = set((_TC.get("seats") or {}).get("present_in_phases") or {})
for _e, _p in _evt_prod.items():
    _ps = str(_p)
    for _ref in re.findall(r"seat:([A-Za-z0-9_-]+)", _ps):
        if _ref not in _SEATS_DEF:
            fail(f"team-collaboration: 事件 '{_e}' 生产者 seat:{_ref} 不在 seats.present_in_phases（悬空座位——ADR-0022）")
    for _ref in re.findall(r"agent:([A-Za-z0-9_-]+)", _ps):
        if _ref not in agents:
            fail(f"team-collaboration: 事件 '{_e}' 生产者 agent:{_ref} 不存在（悬空引用——ADR-0022）")

# ── per-change_class 相位可达性（ADR-0022：issue #31 C-1——分类死锁灭绝）──
# review 裁定按 dispatch 表分派；事件可用性=基础集（platform/机制/owner 生产，排除
# review.*）∪ dispatch 决定的 review 事件。对每个 change_class 从 plan 求解 handoff 可达。
_CC = (load_yaml(ROOT / "standards" / "change-classes.yaml") or {}).get("classes") or {}
_dispatch = ((((_TC.get("flow") or {}).get("verdict_layers") or {}).get("review") or {}).get("dispatch")) or {}
if _dispatch and _graph and _order and _evt_prod:
    def _edge_open(when, available):
        """CNF 求值（AND of OR）：事件 token ∈ available；状态/函数条件
        （planner.state==exited、no_release_face(wave)）视为 True——由其余防线保证。"""
        for _clause in str(when).split("AND"):
            _clause_val = False
            for _alt in _clause.split("OR"):
                _t = _alt.strip(" ()\t")
                if "." not in _t or " " in _t or _t.startswith(("planner.", "builder.", "wave.")):
                    _clause_val = True       # 非事件条件（状态断言/函数）——不阻塞
                elif _t in available:
                    _clause_val = True
            if not _clause_val:
                return False
        return True

    _base_events = {_ev for _ev, _p in _evt_prod.items()
                    if not _ev.startswith("review.")
                    and (str(_p).startswith(("platform", "owner")) or str(_p).startswith("mechanism:"))}
    _ledger_cc_text = ((ROOT / "standards" / "attention-ledger.yaml").read_text(encoding="utf-8")
                       + (ROOT / "standards" / "change-classes.yaml").read_text(encoding="utf-8"))
    for _cc in _CC:
        _d = _dispatch.get(_cc)
        if not isinstance(_d, dict):
            fail(f"verdict_layers.review.dispatch 缺 change_class '{_cc}' 条目（相位可达性不可解——ADR-0022）")
            continue
        _seat = str(_d.get("seat") or "")
        if _d.get("mode") == "seat" and _seat not in _SEATS_DEF:
            fail(f"review.dispatch.{_cc}.seat '{_seat}' 不在 seats.present_in_phases（悬空座位——ADR-0022）")
        for _k in _d.get("extra_keys") or []:   # 合并钥匙必须有主（issue #31 C-2：owner_ratify 类）
            if _k not in _evt_prod and _k not in _ledger_cc_text:
                fail(f"review.dispatch.{_cc}.extra_keys '{_k}' 无事件生产者且无账本/变更类出处（悬空钥匙——ADR-0022）")
        _av = set(_base_events)
        if str(_d.get("mode")) == "waived":
            _av.add("review.waived")
        elif str(_d.get("mode")) == "seat":
            _av.update(("review.approve", "review.changes_requested"))
        _reached, _frontier = {"plan"}, ["plan"]
        while _frontier:
            _cur = _frontier.pop()
            for _e in _graph:
                if str(_e.get("from")) in (_cur, "any") and _edge_open(_e.get("when", ""), _av):
                    _n = str(_e.get("to"))
                    if _n not in _reached:
                        _reached.add(_n)
                        _frontier.append(_n)
        if "handoff" not in _reached:
            fail(f"team-collaboration: change_class '{_cc}' 相位不可达 handoff（reached={sorted(_reached)}，"
                 f"review.dispatch.{_cc}.mode={_d.get('mode')!r}——分类死锁，ADR-0022/issue #31 C-1）")
    for _cc in _dispatch:
        if _cc not in _CC:
            fail(f"verdict_layers.review.dispatch 引用不存在的 change_class '{_cc}'（dispatch 漂移——ADR-0022）")

# services 成员引用：服务型座位绑定的 agent 必须存在且 approved（走查 P1：arbiter proposed 曾逃逸校验）
OK = {"approved", "deprecated"}
ACTIVE = {"approved", "active"}
for _svc, _sdef in ((_TC.get("services") or {}).items()):
    for _m in (_sdef.get("members") or []) if isinstance(_sdef, dict) else []:
        _aid = str(_m).removeprefix("agent:").split("@")[0]
        _ag = agents.get(_aid)
        if _ag is None:
            fail(f"services.{_svc} 绑定不存在的 agent:{_aid}")
        elif _ag.get("status") not in OK:
            fail(f"services.{_svc} 绑定未批准的 agent:{_aid} (status={_ag.get('status')})")

# profiles 字段取值域（防 agent 与 profile 同时用错值时仍通过——CodeRabbit #5）
_ENUMS = {
    "isolation": {"private", "hermetic", "team"},
    "approval": {"auto", "ask_risky", "ask_per_action", "async_notify"},
    "trust_zone": {"untrusted_ingest", "trusted_control"},
}
for _arch, _prof in PROFILES.items():
    for _f, _vals in _ENUMS.items():
        _v = _prof.get(_f)
        if _v is not None and _v not in _vals:
            fail(f"profile:{_arch} {_f}={_v!r} 不在合法取值域 {sorted(_vals)}")
    # profile 白名单 ⊆ 词表（ADR-0022：agent 侧查词表而 profile 侧曾不查——双错可抵消）
    _pv = set(((_prof.get("capabilities") or {}).get("allow")) or [])
    _pbad = _pv - VOCAB
    if _pbad:
        fail(f"profile:{_arch} capabilities.allow 含词表外副作用: {sorted(_pbad)}（side-effects.yaml v2，ADR-0022）")

# ---- gateway 配置对齐（ADR-0002 rev1）----
GW_CFG = DATA / "deploy" / "llm-gateway" / "config.yaml"
if GW_CFG.exists():
    gwc = load_yaml(GW_CFG) or {}
    gw_aliases = {m.get("model_name") for m in gwc.get("model_list", []) or []}
    if gw_aliases != model_aliases:
        fail(f"deploy/llm-gateway/config.yaml 的别名 {sorted(gw_aliases)} 与 models.yaml {sorted(model_aliases)} 不一致（ADR-0002 rev1）")

# ---- profiles 自检：structural 三字段非空 + CT 登记（CT-ADV-003）----
LLM_ARCHETYPES = set()
MECHANISM_ARCHETYPES = set()
for arch, prof in PROFILES.items():
    kind = prof.get("kind")
    if kind == "llm":
        LLM_ARCHETYPES.add(arch)
    elif kind == "mechanism":
        MECHANISM_ARCHETYPES.add(arch)
    for s in (prof.get("duty_assurance") or {}).get("structural") or []:
        if isinstance(s, str):
            fail(f"profile:{arch} structural 仍为 v1 字符串形式（须为 {{claim, enforced_by, control_test}}，ADR-0010）")
            continue
        if not (s.get("claim") and s.get("enforced_by") and s.get("control_test")):
            fail(f"profile:{arch} 存在缺 claim/enforced_by/control_test 的 structural 条目（ADR-0010）")
            continue
        if s["control_test"] not in CT_REG:
            fail(f"profile:{arch} structural 引用的 {s['control_test']} 未在 control-tests.yaml 登记（ct-coverage）")

# ct-coverage 反向：登记但无任何 profile 引用的 CT = 漂移（CT-ADV-003 一一对应——CodeRabbit #5）
_referenced = set()
for _prof in PROFILES.values():
    for _s in ((_prof.get("duty_assurance") or {}).get("structural") or []):
        if isinstance(_s, dict) and _s.get("control_test"):
            _referenced.add(_s["control_test"])
for _ct in set(CT_REG) - _referenced:
    fail(f"control-tests.yaml 登记 {_ct} 未被任何 profile structural 引用（ct-coverage 反向，一一对应）")

# ---- 机制命名绑定与引用完整性（ADR-0021：红队批次3——ghost 机制/命名三态灭绝）----
# ① services 下划线键 ↔ 机制原型连字符 id 互译（kind=mechanism 的服务块必带 id）
# ② 一切 mechanism:X 引用必须解析到机制原型（悬空机制=角色无法被触发的门禁盲区）
# ③ 团队原型 services 列表必须解析到 services 块（被引用才被声明）
_services = _TC.get("services") or {}
for _svc, _sdef in _services.items():
    if not isinstance(_sdef, dict) or not str(_sdef.get("kind", "")).startswith("mechanism"):
        continue
    _mid = _sdef.get("id")
    if not _mid:
        fail(f"services.{_svc} kind=mechanism 缺 id（须=archetype-profiles 机制原型键——命名绑定单一真源，ADR-0021）")
    elif _mid not in MECHANISM_ARCHETYPES:
        fail(f"services.{_svc} id={_mid!r} 不是机制原型（archetype-profiles 无此 mechanism 键，ADR-0021）")
    elif _svc != _mid.replace("-", "_"):
        fail(f"services.{_svc} 与其 id={_mid!r} 不互译（键=下划线形式——同实体三种写法即漂移，ADR-0021）")
_mech_re = re.compile(r"mechanism:([A-Za-z][A-Za-z0-9_-]*)")
for scope_root, rel_root in ((ROOT / "standards", ROOT), (REG, DATA)):
    if not scope_root.is_dir():
        continue
    for p in scope_root.rglob("*.yaml"):
        for m in _mech_re.finditer(p.read_text(encoding="utf-8")):
            ref = m.group(1)
            if ref not in MECHANISM_ARCHETYPES:
                fail(f"{p.relative_to(rel_root)} 引用 mechanism:{ref} 无机制原型（ghost 机制——被依赖却不存在的执行者，ADR-0021）")
for _proto, _pdef in (_TC.get("teams") or {}).items():
    if not isinstance(_pdef, dict):
        continue
    for _s in (_pdef.get("services") or []):
        if str(_s).rstrip("*") not in _services:
            fail(f"teams.{_proto}.services 引用不存在的 services 块: {_s}（团队依赖的服务无声明=运行无主，ADR-0021）")

# ---- 幽灵角色检测（ADR-0021：approved agent 必须有消费方——声明有主运行无主即漂移）----
_bound_agents = set()
for _t in teams.values():
    _ms = _t.get("members")
    if isinstance(_ms, list):
        for _m in _ms:
            if isinstance(_m, dict) and isinstance(_m.get("agent"), str):
                _bound_agents.add(re.sub(r"^registry:", "", _m["agent"]).removeprefix("agent:").split("@")[0])
for _sdef in _services.values():
    if isinstance(_sdef, dict) and isinstance(_sdef.get("members"), list):
        for _m in _sdef["members"]:
            _bound_agents.add(str(_m).removeprefix("agent:").split("@")[0])
for _a in agents.values():
    _refs = ((_a.get("capabilities") or {}).get("agent_tools") or {}).get("refs")
    if isinstance(_refs, list):
        for _r in _refs:
            _bound_agents.add(str(_r).removeprefix("agent:").split("@")[0])
for _aid, _a in agents.items():
    if _a.get("status") == "approved" and _aid not in _bound_agents:
        fail(f"agent:{_aid} approved 但无任何团队/服务/agent_tools 引用（幽灵角色——无触发路径的声明，ADR-0021）")

# ---- 上下文装配与记忆契约（ADR-0018）----
# spawn manifest：装配覆盖一切 LLM 原型；组件 ⊆ 词表；memory_view ⟺ 记忆类型非空。
# simulate 测相位/权限/预算、gate 测产品代码——本块管"agent 启动时拿到什么"的声明层。
CA = load_yaml(ROOT / "standards" / "context-assembly.yaml") or {}
CA_COMPONENTS = set((CA.get("components") or {}).keys())
CA_ASSEMBLY = CA.get("assembly") or {}
CA_MEM = (CA.get("memory") or {}).get("per_archetype") or {}
CA_MEM_ENUM = set((CA.get("memory") or {}).get("types_enum") or [])
if not CA:
    fail("standards/context-assembly.yaml 缺失或解析为空（ADR-0018——启动上下文未声明）")
for arch in LLM_ARCHETYPES:
    entry = CA_ASSEMBLY.get(arch)
    if not isinstance(entry, dict) or not entry.get("components"):
        fail(f"context-assembly: LLM 原型 {arch} 无装配清单（spawn manifest 缺失——启动上下文未声明，ADR-0018）")
        continue
    comps = entry.get("components") or []
    bad = [c for c in comps if c not in CA_COMPONENTS]
    if bad:
        fail(f"context-assembly: {arch} 装配组件 {bad} 不在组件词表（fail-closed，ADR-0018）")
    mtypes = set((CA_MEM.get(arch) or {}).get("types") or [])
    if ("memory_view" in comps) != bool(mtypes):
        why = "装配了 memory_view 但记忆契约为空" if "memory_view" in comps else "记忆类型非空但未装配 memory_view"
        fail(f"context-assembly: {arch} {why}（组件⟔契约矛盾，ADR-0018）")
    badt = mtypes - CA_MEM_ENUM
    if badt:
        fail(f"context-assembly: {arch} 记忆类型 {sorted(badt)} 不在 types_enum（fail-closed）")
for arch in set(CA_ASSEMBLY) | set(CA_MEM):
    if arch not in LLM_ARCHETYPES:
        fail(f"context-assembly: {arch} 不是 LLM 原型（装配/记忆契约只覆盖 LLM 原型——机制无 spawn 上下文）")
_dgs = (((CA.get("memory") or {}).get("digest") or {}).get("schema")) or ""
if _dgs:
    _dgp = (REG / _dgs).resolve()
    if not _dgp.is_relative_to(REG.resolve()):
        fail(f"context-assembly: memory.digest.schema 逃逸 registry 目录: {_dgs}")
    elif not _dgp.is_file():
        fail(f"context-assembly: memory.digest.schema 文件不存在: {_dgs}")

# ---- agent 校验 ----
for aid, a in agents.items():
    arch = a.get("archetype")
    if arch not in LLM_ARCHETYPES:
        fail(f"agent:{aid} archetype 非法/缺失: {arch}（须为 LLM 原型之一；机制原型不实例化为 agent，ADR-0010）")
    prof = PROFILES.get(arch) or {}
    if not prof:
        continue
    cap = a.get("capabilities") or {}
    # ① 白名单 ⊆ 词表
    allow = set(cap.get("allow") or [])
    bad = allow - VOCAB
    if bad:
        fail(f"agent:{aid} capabilities.allow 含词表外副作用: {sorted(bad)}（side-effects.yaml v2）")
    # ①b capability-whitelist（ADR-0022 实装——issue #31 A-1：变异 K–Q 七组越权曾双门禁全绿）
    #    实例 allow ⊆ profile allow（fail-closed）：原型边界即实例边界。
    #    CT-BLD-002/PLN-002/JDG-001/CUR-001/RSP-001/DEP-001/RES-001 的声明层强制点。
    _prof_allow = set(((prof.get("capabilities") or {}).get("allow")) or [])
    excess = allow - _prof_allow
    if excess:
        fail(f"agent:{aid} capabilities.allow 越出 profile({arch}) 白名单: {sorted(excess)}"
             "（capability-whitelist——原型边界即实例边界，ADR-0022）")
    # ② agent 工具副作用 ⊆ allow（组合规则：工具可见当且仅当其副作用全被放行）
    for ref in cap.get("tools", []) or []:
        t = tools.get(ref.removeprefix("tool:")) or {}
        tfx = set(t.get("side_effects") or []) - {"none"}
        leak = tfx - allow
        if leak:
            fail(f"agent:{aid} 工具 {ref} 副作用 {sorted(leak)} 不在 allow 白名单内（fail-closed，ADR-0010）")
    # ②b 执行通道覆盖（ADR-0022——issue #31 收敛判据 9 / 变异 A、B）：
    #    tool_required 词必须有工具承载（删工具=失能力——防"白名单纸面授权"）；
    #    platform_direct / runtime_builtin 为 side-effects.yaml 显式豁免登记。
    _covered = set()
    for ref in cap.get("tools", []) or []:
        t = tools.get(ref.removeprefix("tool:")) or {}
        _covered |= set(t.get("side_effects") or []) - {"none"}
    _orphan_words = (allow & _TOOL_REQ) - _covered
    if _orphan_words:
        fail(f"agent:{aid} allow 含 tool_required 词 {sorted(_orphan_words)} 但无工具承载"
             "（must/allow 与 tools 的双向覆盖——ADR-0022）")
    _chanless = allow - _ALL_CHANNELS
    if _chanless:
        fail(f"agent:{aid} allow 含无执行通道词 {sorted(_chanless)}（side-effects delivery_channels 词表外——ADR-0022）")
    # ③ agent_tools 白名单 + 上限
    pat = (prof.get("capabilities") or {}).get("agent_tools") or {}
    p_allow, p_max = set(pat.get("allow") or []), pat.get("max", 0)
    refs = [r.removeprefix("agent:").split("@")[0] for r in (cap.get("agent_tools") or {}).get("refs", []) or []]
    if len(set(refs)) > p_max:
        fail(f"agent:{aid} agent_tools 数 {len(set(refs))} 超过 profile 上限 {p_max}")
    for rid in refs:
        rarch = (agents.get(rid) or {}).get("archetype")
        if rarch not in p_allow:
            fail(f"agent:{aid} agent_tools 引用原型 {rarch}({rid}) 不在 profile 白名单 {sorted(p_allow)}（fail-closed）")
    # ④ isolation/approval/trust_zone 与 profile 一致
    for field in ("isolation", "approval", "trust_zone"):
        want = prof.get(field)
        if want and a.get(field) != want:
            fail(f"agent:{aid} {field}={a.get(field)!r} 须为 {want!r}（profile，ADR-0010）")
    # ⑤ requires 点路径
    for path in prof.get("requires") or []:
        if not dig(a, path):
            fail(f"agent:{aid}({arch}) 缺少 profile 必备项: {path}")
    # ⑥ 族级独立性
    ind = prof.get("independence") or {}
    fam = model_family.get((a.get("model") or {}).get("alias"))
    a.setdefault("_family", fam)
    for other in ind.get("distinct_model_family_from") or []:
        a.setdefault("_must_differ_family_from", []).append(other)
    # ⑦ 常规引用
    for ref in cap.get("skills", []) or []:
        sid = ref.removeprefix("skill:")
        if sid not in skills:
            fail(f"agent:{aid} 引用不存在的 skill:{sid}")
        elif skills[sid].get("status") not in OK:
            fail(f"agent:{aid} 引用未批准的 skill:{sid} (status={skills[sid].get('status')})")
    for ref in cap.get("tools", []) or []:
        tid = ref.removeprefix("tool:")
        if tid not in tools:
            fail(f"agent:{aid} 引用不存在的 tool:{tid}")
        elif tools[tid].get("status") not in OK:
            fail(f"agent:{aid} 引用未批准的 tool:{tid} (status={tools[tid].get('status')})")
    for rid in refs:
        if rid not in agents:
            fail(f"agent:{aid} 引用不存在的 agent_tools:{rid}")
        elif agents[rid].get("status") not in OK:
            fail(f"agent:{aid} 引用未批准的 agent_tools:{rid}")
    alias = (a.get("model") or {}).get("alias")
    if alias and alias not in model_aliases:
        fail(f"agent:{aid} 引用未注册的模型 alias: {alias}")
    for key in ("prompt_ref",):
        pr = (a.get("identity") or {}).get(key)
        if pr:
            p = (REG / pr).resolve()
            if not p.is_relative_to(REG.resolve()):
                fail(f"agent:{aid} {key} 逃逸 registry 目录: {pr}")
            elif not p.is_file():
                fail(f"agent:{aid} {key} 文件不存在: {pr}")
    # io_contract.schema_ref 存在性（输出 schema 是信任机制地基——走查 P1：曾集体悬空）
    for side in ("input", "output"):
        sr = ((a.get("io_contract") or {}).get(side) or {}).get("schema_ref")
        if sr:
            sp = (REG / sr).resolve()
            if not sp.is_relative_to(REG.resolve()):
                fail(f"agent:{aid} schema_ref 逃逸 registry 目录: {sr}")
            elif not sp.is_file():
                fail(f"agent:{aid} schema_ref 文件不存在: {sr}")
    # must_run 执行通道（ADR-0022——issue #31 变异 A/B-2：被要求的动作必须有可执行面）：
    #   命令形态 ⟹ 须持 shell 类工具；check: 前缀 ⟹ 须已注册（checks.yaml）
    for _mr in (a.get("guardrails") or {}).get("must_run") or []:
        _m = str(_mr)
        if _m.startswith("check:"):
            if _m.removeprefix("check:") not in _CHECKS_LOADED:
                fail(f"agent:{aid} must_run '{_m}' 引用未注册防线（checks.yaml——悬空强制项，ADR-0022）")
            continue
        if re.match(r"^[a-z0-9_./-]+(\s|$)", _m):     # 命令形态（make check / python3 …）
            _has_shell = any(
                {"shell_sandbox", "shell_host"} &
                (set((tools.get(r.removeprefix("tool:")) or {}).get("side_effects") or []) - {"none"})
                for r in cap.get("tools", []) or [])
            if not _has_shell:
                fail(f"agent:{aid} must_run 命令 '{_m}' 无 shell 类工具可执行（must_run×工具面断层，ADR-0022）")
        else:
            fail(f"agent:{aid} must_run '{_m}' 既非命令形态也非 check: 引用（执行通道未声明，ADR-0022）")
    # 输出 schema 语义（ADR-0022——issue #31 变异 I/J：schema 被换掉≠契约仍在）
    _out_ref = ((a.get("io_contract") or {}).get("output") or {}).get("schema_ref")
    if _out_ref and (REG / _out_ref).is_file():
        try:
            _osch = json.loads((REG / _out_ref).read_text(encoding="utf-8"))
        except Exception:
            _osch = None      # 语法错误由 schema 语法校验块兜底
        if isinstance(_osch, dict):
            _oprops = set(_osch.get("properties") or {})
            if arch == "test-author":   # CT-TA-004：不产 verdict（validate-executed）
                _oid = str(_osch.get("$id", ""))
                if "verdict" in _oid.lower():
                    fail(f"agent:{aid} 输出 schema 指向判决族（{_oid}——test-author 不产 verdict，CT-TA-004，ADR-0022）")
                _vbad = _oprops & {"verdict", "decision", "judgment", "pass", "fail", "approved"}
                if _vbad:
                    fail(f"agent:{aid} 输出 schema 含判决语义字段 {sorted(_vbad)}（test-author 不产 verdict，CT-TA-004，ADR-0022）")
            _must_have = ((prof.get("io_guarantees") or {}).get("output_must_have")) or []
            _missing = [k for k in _must_have if k not in _oprops]
            if _missing:
                fail(f"agent:{aid} 输出 schema {_out_ref} 缺 {arch}.io_guarantees.output_must_have "
                     f"必备字段 {_missing}（输出契约链断裂，ADR-0022）")
    sr = (a.get("workflow") or {}).get("steps_ref")
    if sr:
        s = (REG / sr).resolve()
        if not s.is_relative_to(REG.resolve()):
            fail(f"agent:{aid} steps_ref 逃逸 registry 目录: {sr}")
        elif not s.is_file():
            fail(f"agent:{aid} steps_ref 文件不存在: {sr}")

# ---- 族独立性：全局比对（服务型座位不落任何 team pool——走查 P0：judge 与 test-author 同族曾逃逸 team 级检查）----
_by_arch: dict = {}
for aid, a in agents.items():
    _by_arch.setdefault(a.get("archetype"), []).append(aid)
for aid, a in agents.items():
    need = a.get("_must_differ_family_from") or []
    if need and not a.get("_family"):
        fail(f"agent:{aid} 声明了 independence 但 model.alias 无 family 映射（models.yaml 缺 family？）")
    for arch in need:
        for other in _by_arch.get(arch, []):
            if other == aid:
                continue
            if a.get("_family") and agents[other].get("_family") == a.get("_family"):
                fail(f"agent:{aid}({a.get('archetype')}) 与 agent:{other}({arch}) 同模型族 {a.get('_family')}"
                     f"（族级独立性，全局比对——ADR-0010；team 级检查覆盖不到服务型座位）")

# ---- tool 校验 ----
for tid, t in tools.items():
    fx = set(t.get("side_effects") or []) - {"none"}
    bad = fx - VOCAB
    if bad:
        fail(f"tool:{tid} side_effects 含词表外值: {sorted(bad)}（side-effects.yaml v2）")
    for side in ("input", "output"):
        sr = ((t.get("io_contract") or {}).get(side) or {}).get("schema_ref")
        if sr:
            sp = (REG / sr).resolve()
            if not sp.is_relative_to(REG.resolve()):
                fail(f"tool:{tid} schema_ref 逃逸 registry 目录: {sr}")
            elif not sp.is_file():
                fail(f"tool:{tid} schema_ref 文件不存在: {sr}")

# ---- skill 校验 ----
for sid, s in skills.items():
    for ref in s.get("allowed_tools", []) or []:
        tid = ref.removeprefix("tool:")
        if tid not in tools:
            fail(f"skill:{sid} 引用不存在的 tool:{tid}")
    if not s.get("acceptance"):
        fail(f"skill:{sid} 缺少 acceptance")

# ---- team 校验（v2：test-authors + verdict_by 机制）----
for tm, t in teams.items():
    members = t.get("members")
    if not isinstance(members, list) or not members:
        # 成员下限 1（schema v2 minItems:1 的执行侧）——persistent 团队无成员 =
        # 无人对治理资产负责（ADR-0013，issue #9 P0-1 的机器侧落地）。
        # 类型防御（评审项）：members 为标量等真值非列表 → 结构错误而非崩溃
        fail(f"team:{tm} members 缺失、为空或非列表（成员下限 1，ADR-0013）")
        members = []
    member_ids = []
    for m in members:
        if not isinstance(m, dict) or not isinstance(m.get("agent"), str) or not m.get("agent"):
            fail(f"team:{tm} 存在畸形成员条目: {m!r}（须为 {{agent: agent:<id>, ...}}）")
            continue
        aid = re.sub(r"^registry:", "", m.get("agent", "")).removeprefix("agent:").split("@")[0]
        member_ids.append(aid)
        if aid not in agents:
            fail(f"team:{tm} 引用不存在的 agent:{aid}")
        elif agents[aid].get("status") not in OK:
            fail(f"team:{tm} 引用未批准的 agent:{aid}")
    arch_of = lambda x: (agents.get(x) or {}).get("archetype")  # noqa: E731
    fam_of = lambda x: agents.get(x, {}).get("_family")  # noqa: E731

    # 族级独立性（按 profile 声明比对，不硬编码原型——CodeRabbit #5）：
    # 每个成员 x 的 profile.independence.distinct_model_family_from 列出须异族的原型 A；
    # x 与团队内/验收引用中的 A 实例逐个比族。
    ver = t.get("verification", {})
    authors = [(c.removeprefix("agent:").split("@")[0]) for c in ver.get("test_authors", []) or []]
    pool = list(dict.fromkeys(member_ids + authors))   # 成员 ∪ 验收出题者
    for x in pool:
        prof = PROFILES.get(arch_of(x)) or {}
        need = ((prof.get("independence") or {}).get("distinct_model_family_from")) or []
        if not need:
            continue
        if not fam_of(x):
            fail(f"team:{tm} {x} 的原型声明 independence 但缺 family 映射（ADR-0010）")
        for d in pool:
            if d == x or arch_of(d) not in need:
                continue
            if fam_of(x) and fam_of(d) and fam_of(x) == fam_of(d):
                fail(f"team:{tm} {x}({arch_of(x)}) 与 {d}({arch_of(d)}) 同模型族 {fam_of(x)}（族级独立性，ADR-0010）")

    # AR-9 v2：含 builder 的团队——test_authors + verdict_by 机制 + external_audit
    builders = [a for a in member_ids if arch_of(a) == "builder"]
    if builders:
        if not authors:
            fail(f"team:{tm} 含 builder 成员但未声明 verification.test_authors（AR-9 v2）")
        for c in authors:
            if c not in agents:
                fail(f"team:{tm} 的 test_author 引用不存在的 agent:{c}")
                continue
            if arch_of(c) != "test-author":
                fail(f"team:{tm} 的验收出题者 agent:{c} 不是 test-author 原型（ADR-0010）")
            if c in builders:
                fail(f"team:{tm} 中 agent:{c} 既是 builder 又是 test_author（利益分离）")
        vb = ver.get("verdict_by", "")
        if not str(vb).startswith("mechanism:verifier"):
            fail(f"team:{tm} 未声明 verdict_by: mechanism:verifier（判卷须为机制，ADR-0010）")
        ea = ver.get("external_audit", {})
        if t.get("lifecycle", {}).get("type") == "ephemeral" and not ea.get("team"):
            fail(f"team:{tm} 是 ephemeral 产出型团队但未声明 external_audit（AR-9）")
        eat = (ea.get("team") or "").removeprefix("team:")
        if eat and eat.startswith("null:"):
            pass
        elif eat and (eat not in teams or teams[eat].get("lifecycle", {}).get("type") != "persistent"):
            fail(f"team:{tm} 的 external_audit.team 不是 persistent 团队: {eat}")

    # 生命周期
    life = t.get("lifecycle", {})
    if life.get("type") == "ephemeral":
        target = (life.get("archive_to") or "").removeprefix("team:")
        if not target:
            fail(f"team:{tm} 是 ephemeral 但未声明 archive_to")
        elif target not in teams or teams[target].get("lifecycle", {}).get("type") != "persistent":
            fail(f"team:{tm} 的 archive_to 不是 persistent 团队: {target}")
        if not life.get("handoff"):
            fail(f"team:{tm} 是 ephemeral 但未声明 handoff")
        elif "memory-export" not in [str(x) for x in (life.get("handoff") or [])]:
            fail(f"team:{tm} ephemeral 但 handoff 缺 memory-export（记忆素材须先于 workspace 销毁过界——ADR-0018）")

# ---- tool owner 校验 ----
for tid, t in tools.items():
    owner = t.get("owner", "")
    if owner.startswith("team:"):
        ot = owner.removeprefix("team:")
        if ot not in teams or teams[ot].get("lifecycle", {}).get("type") != "persistent":
            fail(f"tool:{tid} 的 owner 不是 persistent 团队: {owner}")

# ---- 开源项目清单（ADR-0018：供应链单一真源）----
# 工具实现与网关 upstream 必须先入清单（fail-closed——org 名/仓名漂移在此灭绝）；
# 条目必填审计字段（无审计计划=死清单）；反向：无消费者的条目=死条目。
PROJECTS_DOC = load_yaml(REG / "projects.yaml") or {}
_proj_repos: set = set()
for _pr in PROJECTS_DOC.get("projects") or []:
    if not isinstance(_pr, dict):
        fail(f"projects.yaml 存在非对象条目: {_pr!r}")
        continue
    _repo = _pr.get("repo")
    if not (isinstance(_repo, str) and re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", _repo)):
        fail(f"projects.yaml 条目 repo 非法: {_repo!r}（须 owner/name）")
        continue
    _proj_repos.add(_repo)
    for _f in ("role", "license", "pin_policy"):
        if not _pr.get(_f):
            fail(f"projects.yaml 条目 {_repo} 缺 {_f}（清单即审计对象——字段残缺=不可审计）")
    _aud = _pr.get("audit") or {}
    if not (isinstance(_aud, dict) and _aud.get("tool") and _aud.get("schedule")):
        fail(f"projects.yaml 条目 {_repo} 缺 audit.tool/schedule（无审计计划=死清单）")
if not _proj_repos:
    fail("registry/projects.yaml 清单为空或缺失（ADR-0018——工具实现引用无处收敛）")
_repo_consumers: set = set()
for tid, t in tools.items():
    _repo = (t.get("implementation") or {}).get("repo")
    if not _repo:
        fail(f"tool:{tid} 无 implementation.repo（实现不可溯源——ADR-0018）")
        continue
    _repo_consumers.add(_repo)
    if _repo not in _proj_repos:
        fail(f"tool:{tid} implementation.repo '{_repo}' 不在 registry/projects.yaml（供应链漂移——ADR-0018）")
_up_repo = (((load_yaml(REG / "models.yaml") or {}).get("gateway") or {}).get("upstream_runtime") or {}).get("repo")
if _up_repo:
    _repo_consumers.add(_up_repo)
    if _up_repo not in _proj_repos:
        fail(f"models.yaml gateway.upstream_runtime.repo '{_up_repo}' 不在 registry/projects.yaml（供应链漂移——ADR-0018）")
_sdk_repo = (((load_yaml(REG / "models.yaml") or {}).get("gateway") or {}).get("sdk_runtime") or {}).get("repo")
if _sdk_repo:  # ADR-0025：内核 SDK 双上游——与 upstream_runtime 同为 projects.yaml 消费者
    _repo_consumers.add(_sdk_repo)
    if _sdk_repo not in _proj_repos:
        fail(f"models.yaml gateway.sdk_runtime.repo '{_sdk_repo}' 不在 registry/projects.yaml（供应链漂移——ADR-0018）")
for _repo in sorted(_proj_repos - _repo_consumers):
    fail(f"projects.yaml 条目 {_repo} 无任何消费者（tool/gateway 皆未引用——死条目即漂移）")

# ---- check:* 注册表校验（ADR-0012：悬空防线不可声明；ADR-0013：条目结构硬化）----
# standards/ 与 registry/ 中一切 check:<id> 引用必须 ∈ standards/checks.yaml（fail-closed）。
# 文本级扫描：引用嵌在自由文本（description/enforced_by/post_conditions）里，结构遍历会漏。
# 根类型校验已随提前加载（文件头部）完成；此处做条目结构校验。
CHECKS = set()
for _c in CHECKS_REG.get("checks", []) or []:
    # 条目结构校验（ADR-0013，PR#8 qodo 评审项）：畸形条目 fail 而非静默授权——
    # 注册表是防线的单一真源，注册表层自身必须先可信
    if not isinstance(_c, dict):
        fail(f"checks.yaml 存在非对象条目: {_c!r}（条目结构: id/status/where）")
        continue
    _cid = _c.get("id")
    if not (isinstance(_cid, str) and re.fullmatch(r"[a-z][a-z0-9-]*", _cid)):
        fail(f"checks.yaml 条目 id 非法: {_cid!r}（合法语法 ^[a-z][a-z0-9-]*$）")
        continue
    if _cid in CHECKS:
        fail(f"checks.yaml 条目 id 重复: {_cid}")
        continue
    if _c.get("status") not in ("active", "planned"):
        fail(f"checks.yaml 条目 {_cid} status 非法: {_c.get('status')!r}（须为 active|planned）")
    if not _c.get("where"):
        fail(f"checks.yaml 条目 {_cid} 缺 where（实现位置——悬空代价须显式承担）")
    if "consumed_externally" in _c and not isinstance(_c.get("consumed_externally"), bool):
        fail(f"checks.yaml 条目 {_cid} consumed_externally 非布尔: {_c.get('consumed_externally')!r}")
    CHECKS.add(_cid)
if not CHECKS:
    fail("standards/checks.yaml 注册表为空或缺失（ADR-0012）")
# 引用侧完整 token 匹配（ADR-0013，PR#8 qodo 评审项）：
#   捕获 [A-Za-z0-9_-]+ 全串再校验语法——防 `check:gate_typo` 被旧正则
#   ([a-z][a-z0-9-]*) 前缀截断读作已注册的 gate 而静默放行；
#   标识前加词边界——防 `healthcheck:x` 中的 check 片段被误读为防线引用。
# 诊断路径相对各自扫描根（standards→ROOT / registry→DATA）：双 checkout
# （base-validator / head-data）场景下报错路径不串根。
check_re = re.compile(r"(?<![A-Za-z0-9_-])check:([A-Za-z0-9_-]+)")
for scope_root, rel_root in ((ROOT / "standards", ROOT), (REG, DATA)):
    if not scope_root.is_dir():
        continue
    for p in scope_root.rglob("*.yaml"):
        for m in check_re.finditer(p.read_text(encoding="utf-8")):
            ref = m.group(1)
            if ref in CHECKS:
                continue
            hint = "" if re.fullmatch(r"[a-z][a-z0-9-]*", ref) else "（畸形 id——合法语法 ^[a-z][a-z0-9-]*$）"
            fail(f"{p.relative_to(rel_root)} 引用未注册的 check:{ref}{hint}"
                 f"（不在 standards/checks.yaml——悬空防线）")
# 反向：登记但无任何声明引用 = 注册表漂移（与 ct-coverage 反向同模式；
# consumed_externally 的条目消费方在平台仓，跳过）
_scanned = set()
for scope_root, rel_root in ((ROOT / "standards", ROOT), (REG, DATA)):
    if not scope_root.is_dir():
        continue
    for p in scope_root.rglob("*.yaml"):
        if p.name == "checks.yaml":
            continue
        _scanned.update(check_re.findall(p.read_text(encoding="utf-8")))
_ext = {c.get("id") for c in CHECKS_REG.get("checks", []) if isinstance(c, dict) and c.get("consumed_externally")}
for cid in sorted(CHECKS - _scanned - _ext):
    fail(f"checks.yaml 登记 {cid} 未被任何声明引用（注册表漂移——登记项须有消费方）")
# check 降级防护（ADR-0022——issue #31 变异 G）：id 在本仓 CI 有执行点（step name）
# 的防线必须 active——有执行点却标 planned = 状态漂移（防静默摘除）
_wf_text = ""
for _wf in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
    _wf_text += _wf.read_text(encoding="utf-8")
_ci_step_ids = set(re.findall(r"name:\s*([a-z][a-z0-9-]*)", _wf_text))
for _c in CHECKS_REG.get("checks", []) or []:
    if isinstance(_c, dict) and _c.get("id") in _ci_step_ids and _c.get("status") == "planned":
        fail(f"checks.yaml: '{_c['id']}' 在本仓 CI 有执行点但 status=planned（状态漂移——"
             f"有执行点的防线必须 active，ADR-0022）")

# ---- 场景注册表防掏空（ADR-0022——issue #31 A-3/变异 E）----
_SCEN_DOC = load_yaml(ROOT / "standards" / "scenarios.yaml") or {}
_scenarios = _SCEN_DOC.get("scenarios") or {}
for _sid, _spec in _scenarios.items():
    if not isinstance(_spec, dict):
        continue
    if not (_spec.get("asserts") or _spec.get("hook")):
        fail(f"scenario:{_sid} 无 asserts 且无 hook（空壳场景——场景注册表掏空，ADR-0022）")
_floor = ((_SCEN_DOC.get("registry") or {}).get("asserts_floor_total")) if isinstance(_SCEN_DOC.get("registry"), dict) else None
_total_asserts = sum(len(s.get("asserts") or []) for s in _scenarios.values() if isinstance(s, dict))
if _floor is not None and _total_asserts < _floor:
    fail(f"scenarios: 声明式断言总数 {_total_asserts} < asserts_floor_total {_floor}"
         "（断言掏空——下调 floor 须走 C1 PR 显式评审，ADR-0022）")

# ---- workflow 绑定完整性（ADR-0022——issue #31 B-7）----
_steps_refs = set()
for aid, a in agents.items():
    _wf = a.get("workflow") or {}
    if not isinstance(_wf, dict):
        continue
    if _wf.get("mode") == "fixed" and not _wf.get("steps_ref"):
        fail(f"agent:{aid} workflow.mode=fixed 但缺 steps_ref（固定流程必须绑定文件——ADR-0022）")
    if _wf.get("steps_ref"):
        _steps_refs.add(str(_wf["steps_ref"]))
for _wf_file in sorted((REG / "workflows").glob("*.md")):
    if f"workflows/{_wf_file.name}" not in _steps_refs:
        fail(f"registry/workflows/{_wf_file.name} 未被任何 agent steps_ref 引用（孤儿 workflow——ADR-0022）")

# ---- adversary 凭据借用声明（ADR-0022——issue #31 B-5）----
# 存在 adversary-executed CT ⟹ adversary 实例必须声明 credential.impersonation
# （凭据副本签发机制显式化——否则 13 条 CT 的 who 字段物理不可执行）
if any(isinstance(ct, dict) and ct.get("runtime") == "adversary-executed" for ct in CT_REG.values()):
    for _aid, _a in agents.items():
        if _a.get("archetype") == "adversary" and not ((_a.get("credential") or {}).get("impersonation")):
            fail(f"agent:{_aid} 无 credential.impersonation（存在 adversary-executed CT——"
                 f"目标原型凭据副本的签发/销毁须声明化，ADR-0022）")

# ---- intent-routing flow_ref fail-closed（ADR-0022——issue #31 D-3）----
# IR/INTENTS 在下方路由表校验块才定义——以函数封装、由该块尾调用（_check_flow_refs）
def _check_flow_refs() -> None:
    _EXT_REFS = {str(x.get("ref")) for x in (IR.get("external_flow_refs") or []) if isinstance(x, dict)}
    for iid, spec in INTENTS.items():
        if not isinstance(spec, dict):
            continue
        fr = spec.get("flow_ref")
        if not fr:
            fail(f"intent:{iid} 缺 flow_ref（路由表条目不完整——ADR-0022）")
            continue
        fr = str(fr)
        if fr.startswith("external:"):
            if fr not in _EXT_REFS:
                fail(f"intent:{iid} flow_ref '{fr}' 未登记于 external_flow_refs 豁免清单"
                     "（外部引用须显式承担不可审计边界，ADR-0022）")
            continue
        if "#" not in fr:
            fail(f"intent:{iid} flow_ref '{fr}' 缺锚（须 file#anchor 形式，ADR-0022）")
            continue
        _file, _, _anchor = fr.partition("#")
        _fp = None
        for _cand in (ROOT / "standards" / _file, ROOT / _file):
            if _cand.is_file():
                _fp = _cand
                break
        if _fp is None:
            fail(f"intent:{iid} flow_ref 文件不存在: {_file}（fail-closed——ADR-0022）")
            continue
        _fdoc = load_yaml(_fp) or {}
        _cur = _fdoc
        for _seg in str(_anchor).split("."):
            if isinstance(_cur, dict) and _seg in _cur:
                _cur = _cur[_seg]
            else:
                fail(f"intent:{iid} flow_ref 锚不可解析: {fr}（fail-closed——ADR-0022）")
                break

# ---- JSON Schema 语法校验（ADR-0022——issue #31 D-5：语法损坏的 schema 不得过门禁）----
for sp in sorted((REG / "schemas").glob("*.json")):
    try:
        _sch = json.loads(sp.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        fail(f"schema 语法错误: {sp.name}: {e}（io 契约载体必须可解析，ADR-0022）")
        continue
    if not isinstance(_sch, dict) or _sch.get("type") != "object":
        fail(f"schema {sp.name} 顶层须为 type: object（io 契约载体——ADR-0022）")
        continue
    if not isinstance(_sch.get("properties"), dict):
        fail(f"schema {sp.name} 缺 properties 对象（ADR-0022）")
        continue
    _req = _sch.get("required")
    if _req is not None and not isinstance(_req, list):
        fail(f"schema {sp.name} required 须为数组（ADR-0022）")
        continue
    _req_unknown = [k for k in (_req or []) if k not in (_sch.get("properties") or {})]
    if _req_unknown:
        fail(f"schema {sp.name} required 引用未定义字段 {_req_unknown}（ADR-0022）")

# ---- ADR 编号唯一性（ADR-0013：issue #9 P1-6）----
# decisions/ADR-NNNN-slug.md 编号冲突即 FAIL。唯一豁免 = ADR-0011 历史双档
# （ADR-0012 消歧约定：不重编号、引用带主题限定——豁免在代码中显式记录出处）。
# 豁免按精确文件集校验（评审项）：第三个 ADR-0011 文件或历史双档改名/缺失都 fail——
# 豁免只覆盖这对已存在的文件，编号 0011 不因此可复用。
ADR_DUP_EXEMPT = {
    "0011": ("ADR-0011-runtime-egress-monitoring-and-scorecard.md",
             "ADR-0011-team-collaboration-v1.md"),
}
_adr_files: dict = {}
for _adr in sorted((ROOT / "decisions").glob("ADR-*.md")):
    # 完整文件名匹配（评审项）：恰好 4 位数字 + 非空 slug——
    # 防 ADR-12345-x.md（5 位被前缀读作 1234）与 ADR-0013-.md（空 slug）
    _m = re.fullmatch(r"ADR-(\d{4})-(.+)\.md", _adr.name)
    if not _m:
        fail(f"decisions/ 存在畸形 ADR 文件名: {_adr.name}（须为 ADR-NNNN-slug.md，slug 非空）")
        continue
    _adr_files.setdefault(_m.group(1), []).append(_adr.name)
for _num, _files in _adr_files.items():
    if len(_files) > 1:
        _exempt = ADR_DUP_EXEMPT.get(_num)
        if _exempt is None:
            fail(f"ADR 编号冲突: {' 与 '.join(_files)} 共用编号 {_num}（ADR-0013 编号唯一性）")
        elif tuple(sorted(_files)) != tuple(sorted(_exempt)):
            fail(f"编号 {_num} 的多文件集合与豁免历史双档不符: {sorted(_files)}"
                 f"（豁免仅覆盖 {sorted(_exempt)}——改名/增删/新增同号文件均不允许）")

# ---- intent-routing 路由表校验（ADR-0014：路由引用 fail-closed）----
IR = load_yaml(ROOT / "standards" / "intent-routing.yaml") or {}
INTENTS = IR.get("intents") or {}
CHANGE_CLASSES = (load_yaml(ROOT / "standards" / "change-classes.yaml") or {}).get("classes") or {}
TC_TEAMS = (_TC.get("teams") or {})
_valid_sources = set(IR.get("acceptance_sources") or [])
if not INTENTS:
    fail("standards/intent-routing.yaml 路由表缺失或为空（ADR-0014）")
for iid, spec in INTENTS.items():
    if not isinstance(spec, dict):
        continue
    src = spec.get("acceptance_source")
    if src not in _valid_sources:
        fail(f"intent:{iid} acceptance_source '{src}' 不在三分法枚举 {sorted(_valid_sources)}")
    cc = spec.get("change_class")
    if cc and cc not in CHANGE_CLASSES:
        fail(f"intent:{iid} change_class '{cc}' 不在 change-classes.yaml classes（机器不可判定）")
    # carrier 引用的团队原型必须存在于 team-collaboration teams 声明
    carrier = str(spec.get("carrier", ""))
    for proto in ("delivery_squad", "stewardship", "incident_cell"):
        if proto in carrier and proto not in TC_TEAMS:
            fail(f"intent:{iid} carrier 引用不存在的团队原型 {proto}")
# 反向：change-classes 每个新增意图载体类（trivial/spike）必须有意图路由到它
_intent_classes = {spec.get("change_class") for spec in INTENTS.values()
                   if isinstance(spec, dict) and spec.get("change_class")}
for cc in ("trivial", "spike"):
    if cc in CHANGE_CLASSES and cc not in _intent_classes:
        fail(f"change-class '{cc}' 已定义但无 intent 路由到它（孤类——路由表不完整）")
_check_flow_refs()   # ADR-0022：flow_ref fail-closed（IR/INTENTS 已就绪）

# ---- CT ↔ scenario 双向链接校验（ADR-0015：测试底层方法统一）----
# control-tests 每条：scenario=声明层先决场景（必须存在于 scenarios.yaml，可 null）；
# runtime ∈ {adversary-executed, validate-executed, manual_only}（manual_only 须带注释理由）。
# 反向：scenarios.yaml 的 ct_refs 引用必须存在于 control-tests.yaml（悬空引用=漂移）。
SCEN = (load_yaml(ROOT / "standards" / "scenarios.yaml") or {}).get("scenarios") or {}
CT_TESTS = (load_yaml(ROOT / "standards" / "control-tests.yaml") or {}).get("tests") or {}
_valid_rt = {"adversary-executed", "validate-executed", "manual_only"}
for cid, ct in CT_TESTS.items():
    if not isinstance(ct, dict):
        continue
    scen = ct.get("scenario")
    if scen is not None and scen not in SCEN:
        fail(f"{cid} scenario '{scen}' 不在 scenarios.yaml（悬空场景引用）")
    rt = str(ct.get("runtime", ""))
    if rt not in _valid_rt:
        fail(f"{cid} runtime '{rt}' 非法（∈ {sorted(_valid_rt)}）")
    if rt == "manual_only" and not ct.get("runtime_note"):
        fail(f"{cid} runtime=manual_only 无 runtime_note（ADR-0015：显式 manual_only 必须带理由）")
for sid, spec in SCEN.items():
    for ref in (spec.get("ct_refs") or []):
        if ref not in CT_TESTS:
            fail(f"scenario {sid} ct_refs 引用不存在的 {ref}（悬空 CT 引用）")

if errors:
    print(f"FAIL ({len(errors)}):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
print(f"OK: tools={len(tools)} skills={len(skills)} agents={len(agents)} teams={len(teams)} models={len(model_aliases)} "
      f"(llm_archetypes={len(LLM_ARCHETYPES)} mechanisms={len(MECHANISM_ARCHETYPES)} ct={len(CT_REG)})")
