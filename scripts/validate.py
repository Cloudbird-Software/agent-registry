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
for _std in ("flows.yaml", "change-classes.yaml"):
    if (load_yaml(ROOT / "standards" / _std) or {}) == {}:
        fail(f"standards/{_std} 缺失或解析为空（标准文件必须可解析，ADR-0010）")

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

OK = {"approved", "deprecated"}
ACTIVE = {"approved", "active"}

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
    sr = (a.get("workflow") or {}).get("steps_ref")
    if sr:
        s = (REG / sr).resolve()
        if not s.is_relative_to(REG.resolve()):
            fail(f"agent:{aid} steps_ref 逃逸 registry 目录: {sr}")
        elif not s.is_file():
            fail(f"agent:{aid} steps_ref 文件不存在: {sr}")

# ---- 族独立性：跨 agent 比对（team 内成对检查见下；此处查 family 缺失）----
for aid, a in agents.items():
    need = a.get("_must_differ_family_from") or []
    if need and not a.get("_family"):
        fail(f"agent:{aid} 声明了 independence 但 model.alias 无 family 映射（models.yaml 缺 family？）")

# ---- tool 校验 ----
for tid, t in tools.items():
    fx = set(t.get("side_effects") or []) - {"none"}
    bad = fx - VOCAB
    if bad:
        fail(f"tool:{tid} side_effects 含词表外值: {sorted(bad)}（side-effects.yaml v2）")

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
    member_ids = []
    for m in t.get("members", []):
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

if errors:
    print(f"FAIL ({len(errors)}):")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
print(f"OK: tools={len(tools)} skills={len(skills)} agents={len(agents)} teams={len(teams)} models={len(model_aliases)} "
      f"(llm_archetypes={len(LLM_ARCHETYPES)} mechanisms={len(MECHANISM_ARCHETYPES)} ct={len(CT_REG)})")
