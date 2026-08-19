"""snapshot.py / canary.py 元自测（ADR-0021 治理测试回路的自我验证）。

- snapshot：确定性（同树两次渲染字节一致）+ 覆盖面（关键声明文件在快照内）
  + 差分敏感性（篡改声明后 --check 必须失败——差分门禁自身的负向测试）。
- canary：语法可编译 + 检查函数穷举于 main()（新增检查未接线=漂移）。
"""
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

snapshot = importlib.util.spec_from_file_location("snapshot", ROOT / "scripts" / "snapshot.py")
snapshot = importlib.util.module_from_spec(snapshot)
snapshot.__dict__["__file__"] = str(ROOT / "scripts" / "snapshot.py")
snapshot_loader = snapshot.__spec__.loader
snapshot_loader.exec_module(snapshot)


def test_snapshot_deterministic():
    a = snapshot.render(snapshot.build_snapshot())
    b = snapshot.render(snapshot.build_snapshot())
    assert a == b
    assert a.endswith("\n")


def test_snapshot_covers_declarative_surface():
    snap = snapshot.build_snapshot()
    for key in (
        "standards/team-collaboration.yaml",
        "standards/attention-ledger.yaml",
        "standards/scenarios.yaml",
        "registry/teams/dev-wave.yaml",
        "registry/models.yaml",
        "registry/projects.yaml",
    ):
        assert key in snap, f"快照缺 {key}"
    assert len(snap) >= 50


def test_snapshot_check_detects_tamper(tmp_path: Path):
    """篡改任一声明文件后 --check 必须失败（差分门禁的负向注入测试）"""
    tree = tmp_path / "tree"
    shutil.copytree(ROOT, tree, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    target = tree / "standards" / "attention-ledger.yaml"
    target.write_text(target.read_text(encoding="utf-8") + "\n# tamper\nmax_synchronous_per_week: 9\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(tree / "scripts" / "snapshot.py"), "--check"],
        cwd=tree, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 1, "篡改后 --check 仍通过（差分门禁失效）"
    assert "attention-ledger" in result.stdout


def test_canary_module_loads_and_wires_all_checks():
    canary = importlib.util.spec_from_file_location("canary", ROOT / "scripts" / "canary.py")
    canary = importlib.util.module_from_spec(canary)
    canary.__dict__["__file__"] = str(ROOT / "scripts" / "canary.py")
    canary.__spec__.loader.exec_module(canary)
    # main() 接线穷举：声明的检查函数必须全部被调用（漏接线=检查名存实亡）
    import inspect
    src = inspect.getsource(canary.main)
    defined = [n for n in dir(canary) if n.startswith("check_c") and callable(getattr(canary, n))]
    wired = [n for n in defined if n in src]
    assert defined == wired, f"canary 检查未接线: {set(defined) - set(wired)}"
    assert len(defined) == 7
