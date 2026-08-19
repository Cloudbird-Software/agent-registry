"""validate.py 元验证测试套件（ADR-0013——issue #9 P0-2）。

validate.py 是注册层唯一验证器（AR-1/AR-2 执行点），其自身正确性此前无人验证。
本套件提供回归基线：
  - 正向：未修改的仓库树必须全绿（防回归）。
  - 负向：逐项注入缺陷，每项必须被 validate.py 拒绝（exit=1 且命中对应错误信息）
    ——错误放行 bug 在此先行暴露。
运行：python -m pytest tests/ -v（validate.yml gate job 内执行，失败即阻塞合并）。
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent


def run_validate(tree: Path) -> subprocess.CompletedProcess:
    """在指定树内跑该树自带的 validate.py（自洽：标准=数据=同一树）"""
    return subprocess.run(
        [sys.executable, str(tree / "scripts" / "validate.py")],
        cwd=tree, capture_output=True, text=True, timeout=120,
    )


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """完整仓库树副本（排除 .git/缓存）——负向注入的基底"""
    dest = tmp_path / "tree"
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns(
        ".git", "__pycache__", ".pytest_cache"))
    return dest


def load_yaml(path: Path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def dump_yaml(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)


def assert_rejected(result: subprocess.CompletedProcess, *patterns: str) -> None:
    """负向断言：exit=1 且输出命中全部给定模式（正则）"""
    assert result.returncode == 1, (
        f"预期 FAIL 实则通过（错误放行 bug）。stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    for pat in patterns:
        assert re.search(pat, result.stdout), (
            f"未命中预期错误信息 /{pat}/。stdout:\n{result.stdout}")


# ── 正向：基线全绿（防回归）────────────────────────────────────────
def test_pristine_tree_passes():
    """未修改的仓库树必须全绿；ADR-0011 历史双档按豁免放行（编号唯一性不误报）"""
    result = run_validate(ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "FAIL" not in result.stdout


# ── 负向：ADR 编号唯一性（issue #9 P1-6）──────────────────────────
def test_adr_number_conflict_fails(tree: Path):
    """两个同号 ADR（0013 已存在）必须被拒绝"""
    (tree / "decisions" / "ADR-0013-duplicate-slug.md").write_text(
        "# ADR-0013: duplicate\n", encoding="utf-8")
    assert_rejected(run_validate(tree), r"ADR 编号冲突.*0013")

def test_adr_bad_filename_fails(tree: Path):
    """无法解析编号的 ADR 文件名必须被拒绝"""
    (tree / "decisions" / "ADR-XX-broken.md").write_text("# x\n", encoding="utf-8")
    assert_rejected(run_validate(tree), r"畸形 ADR 文件名.*ADR-XX-broken")

def test_adr_empty_slug_fails(tree: Path):
    """ADR-NNNN-.md（空 slug）不得被前缀匹配放行——须完整文件名校验"""
    (tree / "decisions" / "ADR-0014-.md").write_text("# x\n", encoding="utf-8")
    assert_rejected(run_validate(tree), r"畸形 ADR 文件名.*ADR-0014-")

def test_adr_five_digit_number_fails(tree: Path):
    """ADR-12345-x.md（5 位数字）不得被前缀截断读作 1234 而放行"""
    (tree / "decisions" / "ADR-12345-x.md").write_text("# x\n", encoding="utf-8")
    assert_rejected(run_validate(tree), r"畸形 ADR 文件名.*ADR-12345")


# ── 负向：团队成员下限（issue #9 P0-1 的机器侧落地）────────────────
def test_team_without_members_fails(tree: Path):
    """members 缺失 = 无人对产出负责，必须被拒绝"""
    p = tree / "registry" / "teams" / "stewardship.yaml"
    data = load_yaml(p)
    del data["members"]
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"team:stewardship members 缺失、为空或非列表")

def test_team_malformed_member_fails(tree: Path):
    """非 dict 成员条目不得让校验器崩溃或静默通过"""
    p = tree / "registry" / "teams" / "stewardship.yaml"
    data = load_yaml(p)
    data["members"] = ["agent:curator-main"]
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"畸形成员条目")

def test_team_scalar_members_fails(tree: Path):
    """members: true（真值标量）必须报结构错误而非 TypeError 崩溃"""
    p = tree / "registry" / "teams" / "stewardship.yaml"
    data = load_yaml(p)
    data["members"] = True
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"members 缺失、为空或非列表")

def test_team_nonstring_agent_member_fails(tree: Path):
    """成员 agent 为非字符串值（如 1）必须报结构错误而非 re.sub 崩溃"""
    p = tree / "registry" / "teams" / "stewardship.yaml"
    data = load_yaml(p)
    data["members"] = [{"agent": 1}]
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"畸形成员条目")


# ── 负向：check:* 防线注册表（ADR-0012/0013）──────────────────────
def test_dangling_check_ref_fails(tree: Path):
    """引用未注册的 check = 悬空防线，必须被拒绝"""
    p = tree / "registry" / "teams" / "stewardship.yaml"
    p.write_text(p.read_text(encoding="utf-8") + "\n# 防线：check:not-registered\n",
                 encoding="utf-8")
    assert_rejected(run_validate(tree), r"引用未注册的 check:not-registered")

def test_malformed_check_ref_full_token(tree: Path):
    """`check:gate_typo` 必须整体匹配后报错——不得前缀截断读作已注册的 gate 而放行"""
    p = tree / "registry" / "teams" / "stewardship.yaml"
    p.write_text(p.read_text(encoding="utf-8") + "\n# 防线：check:gate_typo\n",
                 encoding="utf-8")
    assert_rejected(run_validate(tree), r"check:gate_typo")

def test_healthcheck_word_not_matched(tree: Path):
    """`healthcheck:x` 非 check 引用，不得误报（词边界防误匹配）"""
    p = tree / "registry" / "teams" / "stewardship.yaml"
    p.write_text(p.read_text(encoding="utf-8") + "\n# 健康探针：healthcheck:x\n",
                 encoding="utf-8")
    result = run_validate(tree)
    assert result.returncode == 0, result.stdout
    assert "healthcheck" not in result.stdout

def test_checks_registry_bad_id_fails(tree: Path):
    """注册表条目 id 非法必须被拒绝（畸形条目不得静默授权）"""
    p = tree / "standards" / "checks.yaml"
    data = load_yaml(p)
    data["checks"].append({"id": "Bad_ID", "status": "active", "where": "x"})
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"条目 id 非法.*Bad_ID")

def test_checks_registry_bad_status_missing_where_fails(tree: Path):
    """条目 id 合法但 status 非法/缺 where 必须被拒绝（缺陷逐项报出，不短路）"""
    p = tree / "standards" / "checks.yaml"
    data = load_yaml(p)
    data["checks"].append({"id": "extra-check", "status": "maybe"})
    dump_yaml(p, data)
    assert_rejected(run_validate(tree),
                    r"extra-check status 非法.*maybe", r"extra-check 缺 where")

def test_checks_registry_list_root_fails(tree: Path):
    """checks.yaml 根节点为列表必须报结构错误而非 AttributeError 崩溃"""
    p = tree / "standards" / "checks.yaml"
    dump_yaml(p, [{"id": "gate", "status": "active", "where": "x"}])
    assert_rejected(run_validate(tree), r"checks.yaml 根节点须为对象")

def test_checks_registry_scalar_checks_fails(tree: Path):
    """checks: true（标量）必须报结构错误而非 TypeError 崩溃"""
    p = tree / "standards" / "checks.yaml"
    dump_yaml(p, {"version": 1, "checks": True})
    assert_rejected(run_validate(tree), r"checks.yaml 的 checks 须为列表")


# ── 负向：引用完整性（回归既有防线——改验证器时防破坏）──────────────
def test_agent_dangling_tool_ref_fails(tree: Path):
    """agent 引用不存在的 tool 必须被拒绝"""
    p = tree / "registry" / "agents" / "reviewer.yaml"
    data = load_yaml(p)
    data["capabilities"]["tools"] = ["tool:nonexistent"]
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"引用不存在的 tool:nonexistent")

def test_agent_unregistered_model_alias_fails(tree: Path):
    """agent 引用未注册模型 alias 必须被拒绝"""
    p = tree / "registry" / "agents" / "reviewer.yaml"
    data = load_yaml(p)
    data["model"]["alias"] = "no-such-model"
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"未注册的模型 alias: no-such-model")

def test_family_independence_violation_fails(tree: Path):
    """test-author 与 builder 同模型族必须被拒绝（族级独立性——全局比对）"""
    p = tree / "registry" / "agents" / "reviewer.yaml"
    data = load_yaml(p)
    data["model"]["alias"] = "coder-fast"   # flash-family，与 builder 同族
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"同模型族 flash-family")

def test_ephemeral_missing_archive_to_fails(tree: Path):
    """ephemeral 团队缺 archive_to 必须被拒绝（AR-6）"""
    p = tree / "registry" / "teams" / "dev-wave.yaml"
    data = load_yaml(p)
    del data["lifecycle"]["archive_to"]
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"team:dev-wave 是 ephemeral 但未声明 archive_to")


# ── 负向：上下文装配/记忆契约（ADR-0018）─────────────────────────
def test_archetype_without_assembly_fails(tree: Path):
    """LLM 原型缺装配清单 = 启动上下文未声明，必须被拒绝"""
    p = tree / "standards" / "context-assembly.yaml"
    data = load_yaml(p)
    del data["assembly"]["builder"]
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"builder 无装配清单")

def test_assembly_component_out_of_vocab_fails(tree: Path):
    """装配组件不在词表 = fail-closed 违反，必须被拒绝"""
    p = tree / "standards" / "context-assembly.yaml"
    data = load_yaml(p)
    data["assembly"]["builder"]["components"].append("secret_dump")
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"builder 装配组件.*secret_dump.*不在组件词表")

def test_memory_view_contract_mismatch_fails(tree: Path):
    """judge 装配 memory_view 但记忆契约为空 = 组件⟔契约矛盾，必须被拒绝"""
    p = tree / "standards" / "context-assembly.yaml"
    data = load_yaml(p)
    data["assembly"]["judge"]["components"].append("memory_view")
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"judge 装配了 memory_view 但记忆契约为空")

def test_memory_type_out_of_enum_fails(tree: Path):
    """记忆类型不在 types_enum = fail-closed 违反，必须被拒绝"""
    p = tree / "standards" / "context-assembly.yaml"
    data = load_yaml(p)
    data["memory"]["per_archetype"]["builder"]["types"].append("procedural")
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"builder 记忆类型.*procedural.*不在 types_enum")

def test_ephemeral_missing_memory_export_fails(tree: Path):
    """ephemeral 团队 handoff 缺 memory-export = 素材随销毁消失，必须被拒绝"""
    p = tree / "registry" / "teams" / "dev-wave.yaml"
    data = load_yaml(p)
    data["lifecycle"]["handoff"] = [x for x in data["lifecycle"]["handoff"] if x != "memory-export"]
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"team:dev-wave ephemeral 但 handoff 缺 memory-export")

def test_digest_schema_dangling_fails(tree: Path):
    """memory.digest.schema 悬空 = 素材契约无 schema，必须被拒绝"""
    p = tree / "standards" / "context-assembly.yaml"
    data = load_yaml(p)
    data["memory"]["digest"]["schema"] = "schemas/no-such-digest.json"
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"memory.digest.schema 文件不存在")


# ── 负向：开源项目清单（ADR-0018 供应链）─────────────────────────
def test_tool_repo_not_in_projects_fails(tree: Path):
    """工具实现 repo 不在清单 = 供应链漂移（org 名/仓名漂移在此灭绝）"""
    p = tree / "registry" / "tools" / "bash.yaml"
    data = load_yaml(p)
    data["implementation"]["repo"] = "ghost-org/typo-repo"
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"tool:bash implementation.repo 'ghost-org/typo-repo' 不在 registry/projects.yaml")

def test_tool_without_implementation_repo_fails(tree: Path):
    """工具缺 implementation.repo = 实现不可溯源，必须被拒绝"""
    p = tree / "registry" / "tools" / "bash.yaml"
    data = load_yaml(p)
    del data["implementation"]
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"tool:bash 无 implementation.repo")

def test_project_dead_entry_fails(tree: Path):
    """清单条目无任何消费者 = 死条目即漂移，必须被拒绝（与 ct-coverage 反向同模式）"""
    p = tree / "registry" / "projects.yaml"
    data = load_yaml(p)
    data["projects"].append({
        "repo": "org/unused-dep", "role": "x", "license": "MIT",
        "pin_policy": "deploy-time-pin",
        "audit": {"tool": "osv-scanner", "schedule": "weekly"},
    })
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"org/unused-dep 无任何消费者")

def test_project_missing_license_fails(tree: Path):
    """清单条目缺 license = 不可审计，必须被拒绝"""
    p = tree / "registry" / "projects.yaml"
    data = load_yaml(p)
    del data["projects"][0]["license"]
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"openJiuwen-ai/jiuwenswarm 缺 license")


# ── 负向：机制命名绑定与引用完整性（ADR-0021）─────────────────────
def test_dangling_mechanism_ref_fails(tree: Path):
    """mechanism:引用无机制原型 = ghost 机制，必须被拒绝"""
    p = tree / "standards" / "team-collaboration.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace(
        "gate.pass:                  mechanism:verifier",
        "gate.pass:                  mechanism:ghost-engine"),
        encoding="utf-8")
    assert_rejected(run_validate(tree), r"引用 mechanism:ghost-engine 无机制原型")

def test_mechanism_service_without_binding_id_fails(tree: Path):
    """kind=mechanism 服务块缺 id = 命名绑定断链，必须被拒绝"""
    p = tree / "standards" / "team-collaboration.yaml"
    data = load_yaml(p)
    del data["services"]["card_gate"]["id"]
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"services.card_gate kind=mechanism 缺 id")

def test_mechanism_service_bad_binding_fails(tree: Path):
    """服务块 id 指向不存在的机制原型，必须被拒绝"""
    p = tree / "standards" / "team-collaboration.yaml"
    data = load_yaml(p)
    data["services"]["card_gate"]["id"] = "no-such-prototype"
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"services.card_gate id='no-such-prototype' 不是机制原型")

def test_team_services_dangling_ref_fails(tree: Path):
    """团队原型 services 引用不存在的服务块，必须被拒绝"""
    p = tree / "standards" / "team-collaboration.yaml"
    data = load_yaml(p)
    data["teams"]["delivery_squad"]["services"] = ["card_gate", "phantom_service"]
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"teams.delivery_squad.services 引用不存在的 services 块: phantom_service")


# ── 负向：幽灵角色检测（ADR-0021）─────────────────────────────────
def test_orphan_approved_agent_fails(tree: Path):
    """approved agent 无任何团队/服务/agent_tools 引用 = 幽灵角色，必须被拒绝"""
    ghost = tree / "registry" / "agents" / "ghost-role.yaml"
    shutil.copy(tree / "registry" / "agents" / "responder.yaml", ghost)
    data = load_yaml(ghost)
    data["id"] = "ghost-role"
    # 换 alias 避免撞独立性检查；本质仍是全量字段合法但无消费方的 approved 声明
    data["model"]["alias"] = "coder-deep"
    dump_yaml(ghost, data)
    assert_rejected(run_validate(tree), r"agent:ghost-role approved 但无任何团队/服务/agent_tools 引用")
