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
CT_REG = (load_yaml(ROOT / "standards" / "control-tests.yaml") or {}).get("tests", {})
# 标准文件可解析性（flows/change-classes 暂无结构校验，先保证解析不失败——CodeRabbit #5）
for _std in ("flows.yaml", "change-classes.yaml", "team-collaboration.yaml", "attention-ledger.yaml"):
    if (load_yaml(ROOT / "standards" / _std) or {}) == {}:
        fail(f"standards/{_std} 缺失或解析为空（标准文件必须可解析，ADR-0010）")

# attention-ledger 断言（team-collaboration v1.0：conservation_rule 的硬表达）
_LEDGER = load_yaml(ROOT / "standards" / "attention-ledger.yaml") or {}
_sync = _LEDGER.get("synchronous") or []
_max = _LEDGER.get("max_synchronous_per_week")
if _max is not None and len(_sync) > _max:
    fail(f"attention-ledger: synchronous 阻塞点 {len(_sync)} 个 > 上限 {_max}（conservation_rule 违反——新增必须移除一个）")
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
        if not any(str(e.get("from")) in (_ph, "any") and e.get("when") is not None for e in _graph):
            fail(f"team-collaboration: phase '{_ph}' 无出边（死锁相位）")

# 相位图事件的生产者完整性（flow.event_producers——悬空事件=状态机不可执行）
_evt_prod = (_TC.get("flow") or {}).get("event_producers") or {}
for _e in _graph:
    for _tok in str(_e.get("when", "")).replace("AND", " ").replace("OR", " ").split():
        _k = _tok.rstrip(")").split("(")[0].strip()
        if _k and "." in _k and _k not in _evt_prod and not _k.startswith(("planner", "builder", "wave")):
            fail(f"team-collaboration: 相位边事件 '{_k}' 无生产者（flow.event_producers 缺项）")

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
    # ② agent 工具副作用 ⊆ allow（组合规则：工具可见当且仅当其副作用全被放行）
    for ref in cap.get("tools", []) or []:
        t = tools.get(ref.removeprefix("tool:")) or {}
        tfx = set(t.get("side_effects") or []) - {"none"}
        leak = tfx - allow
        if leak:
            fail(f"agent:{aid} 工具 {ref} 副作用 {sorted(leak)} 不在 allow 白名单内（fail-closed，ADR-0010）")
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

# ---- tool owner 校验 ----
for tid, t in tools.items():
    owner = t.get("owner", "")
    if owner.startswith("team:"):
        ot = owner.removeprefix("team:")
        if ot not in teams or teams[ot].get("lifecycle", {}).get("type") != "persistent":
            fail(f"tool:{tid} 的 owner 不是 persistent 团队: {owner}")

# ---- check:* 注册表校验（ADR-0012：悬空防线不可声明；ADR-0013：条目结构硬化）----
# standards/ 与 registry/ 中一切 check:<id> 引用必须 ∈ standards/checks.yaml（fail-closed）。
# 文本级扫描：引用嵌在自由文本（description/enforced_by/post_conditions）里，结构遍历会漏。
CHECKS_REG = load_yaml(ROOT / "standards" / "checks.yaml") or {}
# 根类型校验（评审项）：YAML 可解析为任意类型——列表/标量根须报结构错误而非崩溃
if not isinstance(CHECKS_REG, dict):
    fail(f"checks.yaml 根节点须为对象（version/checks），实为 {type(CHECKS_REG).__name__}")
    CHECKS_REG = {}
elif not isinstance(CHECKS_REG.get("checks"), list):
    fail(f"checks.yaml 的 checks 须为列表，实为 {type(CHECKS_REG.get('checks')).__name__}")
    CHECKS_REG["checks"] = []
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

if errors:
    print(f"FAIL ({len(errors)}):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
print(f"OK: tools={len(tools)} skills={len(skills)} agents={len(agents)} teams={len(teams)} models={len(model_aliases)} "
      f"(llm_archetypes={len(LLM_ARCHETYPES)} mechanisms={len(MECHANISM_ARCHETYPES)} ct={len(CT_REG)})")
