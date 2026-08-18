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
    assert_rejected(run_validate(tree), r"无法解析编号的 ADR 文件名")


# ── 负向：团队成员下限（issue #9 P0-1 的机器侧落地）────────────────
def test_team_without_members_fails(tree: Path):
    """members 缺失 = 无人对产出负责，必须被拒绝"""
    p = tree / "registry" / "teams" / "stewardship.yaml"
    data = load_yaml(p)
    del data["members"]
    dump_yaml(p, data)
    assert_rejected(run_validate(tree), r"team:stewardship members 缺失或为空")

def test_team_malformed_member_fails(tree: Path):
    """非 dict 成员条目不得让校验器崩溃或静默通过"""
    p = tree / "registry" / "teams" / "stewardship.yaml"
    data = load_yaml(p)
    data["members"] = ["agent:curator-main"]
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
