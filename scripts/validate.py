#!/usr/bin/env python3
"""registry 声明校验：YAML 可解析 + 引用完整性 + 状态门禁 + 生命周期规则。
退出码非 0 = CI 拒绝。对应 GOVERNANCE AR-2 / AR-6。"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "registry"
errors = []


def fail(msg: str) -> None:
    errors.append(msg)


def alias_of(a: dict):
    """读取 agent 的 model.alias；model 为 null/缺失 时返回 None（不抛异常）"""
    return (a.get("model") or {}).get("alias")


def dig(d, path: str):
    """按点路径取值；任一层非 dict 即返回 None（ADR-0009 profile.requires 消费）"""
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


# ---- 加载全部条目 ----
tools = {p.stem: load_yaml(p) or {} for p in (REG / "tools").glob("*.yaml")}
agents = {p.stem: load_yaml(p) or {} for p in (REG / "agents").glob("*.yaml")}
teams = {p.stem: load_yaml(p) or {} for p in (REG / "teams").glob("*.yaml")}
skills = {p.parent.name: frontmatter(p) for p in (REG / "skills").glob("*/SKILL.md")}
models = (load_yaml(REG / "models.yaml") or {}).get("models", [])
model_aliases = {m.get("alias") for m in models}

# ---- gateway 配置对齐（ADR-0002 rev1）：别名集合与 models.yaml 完全一致 ----
GW_CFG = ROOT / "deploy" / "llm-gateway" / "config.yaml"
if GW_CFG.exists():
    gwc = load_yaml(GW_CFG) or {}
    gw_aliases = {m.get("model_name") for m in gwc.get("model_list", []) or []}
    if gw_aliases != model_aliases:
        fail(f"deploy/llm-gateway/config.yaml 的别名 {sorted(gw_aliases)} 与 models.yaml {sorted(model_aliases)} 不一致（ADR-0002 rev1）")

# ---- archetype profiles（ADR-0009）：内部构成与职责保证的可执行标准 ----
PROFILES = (load_yaml(ROOT / "standards" / "archetype-profiles.yaml") or {}).get("profiles", {})

OK = {"approved", "deprecated"}  # deprecated 仍可被既有声明引用，但新引用报警
ACTIVE = {"approved", "active"}

# ---- agent 校验 ----
ARCHETYPES = {"builder", "planner", "checker", "judge", "orchestrator", "curator", "interface", "observer", "researcher", "operator"}
for aid, a in agents.items():
    arch = a.get("archetype")
    if arch not in ARCHETYPES:
        fail(f"agent:{aid} archetype 非法或缺失: {arch}（AR-8）")
    if arch == "checker":
        if a.get("workspace", {}).get("scope") != "private":
            fail(f"agent:{aid} 是 checker 但 workspace.scope != private（AR-8 利益分离）")
        if a.get("permissions", {}).get("mode") != "strict":
            fail(f"agent:{aid} 是 checker 但 permissions.mode != strict（AR-8）")
    # ---- profile 机器强制（ADR-0009）----
    prof = PROFILES.get(arch) or {}
    if not prof:
        fail(f"agent:{aid} 的 archetype '{arch}' 在 standards/archetype-profiles.yaml 中无 profile")
    for path in prof.get("requires") or []:
        if not dig(a, path):
            fail(f"agent:{aid}({arch}) 缺少 profile 必备项: {path}（ADR-0009）")
    pm = prof.get("permissions_mode")
    if pm and a.get("permissions", {}).get("mode") != pm:
        fail(f"agent:{aid}({arch}) permissions.mode 必须为 {pm}（ADR-0009）")
    banned_fx = set(prof.get("forbidden_tool_effects") or [])
    if banned_fx:
        for ref in a.get("capabilities", {}).get("tools", []) or []:
            t = tools.get(ref.removeprefix("tool:")) or {}
            hit = set(t.get("side_effects") or []) & banned_fx
            if hit:
                fail(f"agent:{aid}({arch}) 禁用带副作用 {sorted(hit)} 的工具 {ref}（ADR-0009）")
    banned_arch = set(prof.get("forbidden_agent_tool_archetypes") or [])
    if banned_arch:
        for ref in a.get("capabilities", {}).get("agent_tools", []) or []:
            rid = ref.removeprefix("agent:").split("@")[0]
            rarch = (agents.get(rid) or {}).get("archetype")
            if rarch in banned_arch:
                fail(f"agent:{aid}({arch}) 禁止 agent_tools 引用 {rarch} 原型（{ref}）（ADR-0009）")
    for ref in a.get("capabilities", {}).get("skills", []) or []:
        sid = ref.removeprefix("skill:")
        if sid not in skills:
            fail(f"agent:{aid} 引用不存在的 skill:{sid}")
        elif skills[sid].get("status") not in OK:
            fail(f"agent:{aid} 引用未批准的 skill:{sid} (status={skills[sid].get('status')})")
    for ref in a.get("capabilities", {}).get("tools", []) or []:
        tid = ref.removeprefix("tool:")
        if tid not in tools:
            fail(f"agent:{aid} 引用不存在的 tool:{tid}")
        elif tools[tid].get("status") not in OK:
            fail(f"agent:{aid} 引用未批准的 tool:{tid} (status={tools[tid].get('status')})")
    alias = alias_of(a)
    if alias and alias not in model_aliases:
        fail(f"agent:{aid} 引用未注册的模型 alias: {alias}")
    for ref in a.get("capabilities", {}).get("agent_tools", []) or []:
        rid = ref.removeprefix("agent:").split("@")[0]
        if rid not in agents:
            fail(f"agent:{aid} 引用不存在的 agent_tools:{rid}")
        elif agents[rid].get("status") not in OK:
            fail(f"agent:{aid} 引用未批准的 agent_tools:{rid} (status={agents[rid].get('status')})")
    pr = (a.get("identity") or {}).get("prompt_ref")
    if pr and not (REG / pr).exists():
        fail(f"agent:{aid} prompt_ref 文件不存在: {pr}")
    sr = (a.get("workflow") or {}).get("steps_ref")
    if sr and not (REG / sr).exists():
        fail(f"agent:{aid} steps_ref 文件不存在: {sr}")

# ---- skill 校验 ----
for sid, s in skills.items():
    for ref in s.get("allowed_tools", []) or []:
        tid = ref.removeprefix("tool:")
        if tid not in tools:
            fail(f"skill:{sid} 引用不存在的 tool:{tid}")
    if not s.get("acceptance"):
        fail(f"skill:{sid} 缺少 acceptance")

# ---- team 校验 ----
for tid, t in teams.items():
    member_ids = []
    for m in t.get("members", []):
        aid = re.sub(r"^registry:", "", m.get("agent", "")).removeprefix("agent:").split("@")[0]
        member_ids.append(aid)
        if aid not in agents:
            fail(f"team:{tid} 引用不存在的 agent:{aid}")
        elif agents[aid].get("status") not in OK:
            fail(f"team:{tid} 引用未批准的 agent:{aid}")
    # AR-8 v2：judge 独立性——仲裁者模型别名不得与争议双方（builder/checker 成员）相同
    judges = [a for a in member_ids if agents.get(a, {}).get("archetype") == "judge"]
    disputants = [a for a in member_ids if agents.get(a, {}).get("archetype") in ("builder", "checker")]
    for j in judges:
        ja = alias_of(agents[j])
        if not ja:
            fail(f"team:{tid} 仲裁者 {j} 缺少 model.alias，无法验证裁决独立性（ADR-0008）")
    for d in disputants:
        if not alias_of(agents[d]):
            fail(f"team:{tid} 争议方 {d} 缺少 model.alias，无法验证裁决独立性（ADR-0008）")
    for j in judges:
        ja = alias_of(agents[j])
        for d in disputants:
            da = alias_of(agents[d])
            if ja and da and ja == da:
                fail(f"team:{tid} 仲裁者 {j} 与争议方 {d} 模型别名相同({ja})，裁决不独立（ADR-0008）")
    # AR-9 验证链：含 builder 的团队必须独立 checker 验收 + 外部审计
    builders = [a for a in member_ids if agents.get(a, {}).get("archetype") == "builder"]
    ver = t.get("verification", {})
    if builders:
        checkers = [(c.removeprefix("agent:").split("@")[0]) for c in ver.get("in_team_check", {}).get("checkers", []) or []]
        if not checkers:
            fail(f"team:{tid} 含 builder 成员但未声明 verification.in_team_check.checkers（AR-9）")
        for c in checkers:
            if c not in agents:
                fail(f"team:{tid} 的 checker 引用不存在的 agent:{c}")
                continue
            if agents[c].get("archetype") != "checker":
                fail(f"team:{tid} 的验收者 agent:{c} 不是 checker 原型（AR-8/9）")
            if c in builders:
                fail(f"team:{tid} 中 agent:{c} 既是 builder 又是验收者（利益分离）")
            ca = alias_of(agents[c])
            for b in builders:
                ba = alias_of(agents[b])
                if ca and ba and ca == ba:
                    fail(f"team:{tid} 验收者 {c} 与 builder {b} 使用相同模型别名 {ca}（独立性不足）")
        ea = ver.get("external_audit", {})
        if t.get("lifecycle", {}).get("type") == "ephemeral" and not ea.get("team"):
            fail(f"team:{tid} 是 ephemeral 产出型团队但未声明 external_audit（AR-9）")
        eat = (ea.get("team") or "").removeprefix("team:")
        if eat and eat.startswith("null:"):
            pass  # owner 直审（仅 persistent 治理团队允许）
        elif eat and (eat not in teams or teams[eat].get("lifecycle", {}).get("type") != "persistent"):
            fail(f"team:{tid} 的 external_audit.team 不是 persistent 团队: {eat}")
    life = t.get("lifecycle", {})
    if life.get("type") == "ephemeral":
        target = (life.get("archive_to") or "").removeprefix("team:")
        if not target:
            fail(f"team:{tid} 是 ephemeral 但未声明 archive_to")
        elif target not in teams or teams[target].get("lifecycle", {}).get("type") != "persistent":
            fail(f"team:{tid} 的 archive_to 不是 persistent 团队: {target}")
        if not life.get("handoff"):
            fail(f"team:{tid} 是 ephemeral 但未声明 handoff")

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
print(f"OK: tools={len(tools)} skills={len(skills)} agents={len(agents)} teams={len(teams)} models={len(model_aliases)}")
