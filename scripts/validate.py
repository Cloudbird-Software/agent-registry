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

OK = {"approved", "deprecated"}  # deprecated 仍可被既有声明引用，但新引用报警
ACTIVE = {"approved", "active"}

# ---- agent 校验 ----
for aid, a in agents.items():
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
    alias = a.get("model", {}).get("alias")
    if alias and alias not in model_aliases:
        fail(f"agent:{aid} 引用未注册的模型 alias: {alias}")

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
    for m in t.get("members", []):
        aid = re.sub(r"^registry:", "", m.get("agent", "")).removeprefix("agent:").split("@")[0]
        if aid not in agents:
            fail(f"team:{tid} 引用不存在的 agent:{aid}")
        elif agents[aid].get("status") not in OK:
            fail(f"team:{tid} 引用未批准的 agent:{aid}")
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
