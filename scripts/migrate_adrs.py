#!/usr/bin/env python3
"""migrate_adrs.py —— 旧 ADR 归档迁移生成器（W1-C1 / ADR-0053 / .github#164）。

从 agent-registry 仓某 commit 读取 decisions/ADR-*.md 全量，产出四件套：
  1. decisions/INDEX.yaml          —— 墓碑索引（机器可读；状态唯一真源）
  2. decisions/ADR-NNNN-slug.md    —— 同名墓碑替换（保留文件名：org-gate/gate
                                       adr-required 按文件名校验，零级联）
  3. <staging>/adr/ADR-NNNN-slug.md —— 字节保真正本（archive 仓 phase 2 推送）
  4. stdout 分类统计表（PR body 素材）

设计要点（ADR-0053）：
  - 源内容一律经 `git show <commit>:<path>` 读取（不读工作区）——幂等可重跑，
    工作区即使已被墓碑覆盖也不影响再生成；phase 2 刷新迁移时对新 main 重跑即可。
  - 字节保真：archive 正本 = 源 blob 原样；sha256 记入 INDEX.content_sha256
    （AC-1"逐条 diff 校验"的机器形态，由 archive 仓 verify_migration.py 闭环）。
  - 状态不写进 archive 文件（保持字节一致），lifecycle/decision_status 只落 INDEX。
  - 生命周期三态默认 active（保守）；overrides.yaml 提供逐文件 override
    （superseded 须带 superseded_by；非 active 须带 rationale）。
  - INDEX entry 为 #96（ADR 实质校验）预留扩展点：可扩展 substantive 字段，
    本脚本不写入，仅锁骨架。
  - 新 ADR 自迁移合入起：正本入 archive + decisions/ 落墓碑 + INDEX 登记。

用法（在 agent-registry 克隆内）：
  python scripts/migrate_adrs.py [--commit <sha>] [--overrides <path>] \
      [--staging <dir>]
  默认 --commit = origin/main（或 HEAD 兜底）；--staging = ../archive-staging。

自检：python -m py_compile scripts/migrate_adrs.py
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

INDEX_NAME = "INDEX.yaml"
ADR_NAME_RE = re.compile(r"^ADR-(\d{4})-(.+)\.md$")
# 标题/状态行解析（兼容中英文字段：ADR-0010/0022 系用"状态"）
H1_RE = re.compile(r"^#\s+ADR-(\d{4}):\s*(.+?)\s*$", re.MULTILINE)
STATUS_RE = re.compile(r"^-\s*(?:status|状态)\s*:\s*(.+?)\s*$", re.MULTILINE)
LIFECYCLES = ("active", "superseded", "archived")


def die(msg: str) -> None:
    print(f"FATAL: {msg}", file=sys.stderr)
    sys.exit(1)


def git(repo: Path, *args: str) -> str:
    """在 repo 内执行 git 命令；失败即 fail-closed。"""
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        die(f"git {' '.join(args[:2])}… 失败: {proc.stderr.strip()[:300]}")
    return proc.stdout


def load_overrides(path: Path | None) -> dict:
    """overrides.yaml：逐文件 lifecycle override。轻量解析（无 yaml 依赖）：
    结构固定（file/lifecycle/superseded_by/rationale 四键），用缩进块解析足矣，
    与 validate.py 的"零三方依赖起步"风格一致。"""
    overrides: dict = {}
    if path is None or not path.exists():
        return overrides
    cur: dict = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" ") and line.endswith(":"):
            if cur:
                overrides[cur["file"]] = cur
                cur = {}
            cur = {"file": line[:-1].strip()}
        elif line.startswith("  ") and cur:
            key, _, val = line.strip().partition(":")
            val = val.strip().strip("'\"")
            if val:
                cur[key.strip()] = val
    if cur:
        overrides[cur["file"]] = cur
    return overrides


def main() -> int:
    ap = argparse.ArgumentParser(description="旧 ADR 归档迁移生成器（ADR-0053）")
    ap.add_argument("--commit", default=None,
                    help="源 commit（默认 origin/main，HEAD 兜底）")
    ap.add_argument("--overrides", default=None,
                    help="overrides.yaml 路径（默认 scripts/migrate_overrides.yaml）")
    ap.add_argument("--staging", default=None,
                    help="archive 正本 staging 目录（默认 <repo>/../archive-staging）")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parent.parent
    root = repo.parent

    # ── 源 commit 解析 ──
    commit = args.commit
    if commit is None:
        try:
            commit = git(repo, "rev-parse", "--verify", "origin/main").strip()
        except SystemExit:
            commit = git(repo, "rev-parse", "--verify", "HEAD").strip()
    commit = git(repo, "rev-parse", "--verify", f"{commit}^{{commit}}").strip()

    # ── 源清单（git ls-tree，不依赖工作区状态）──
    listing = git(repo, "ls-tree", "-r", "--name-only", commit, "--", "decisions/")
    files = sorted(
        name.split("/", 1)[1]
        for name in listing.splitlines()
        if name.startswith("decisions/") and ADR_NAME_RE.match(name.split("/", 1)[1])
        and name.split("/", 1)[1] != INDEX_NAME
    )
    if not files:
        die("源 commit 的 decisions/ 无 ADR-NNNN-slug.md 文件——源 commit 选错？")
    # ADR-0013 编号唯一性豁免：历史双档照常迁移（INDEX 以 file 为主键，编号可重）
    numbers = [ADR_NAME_RE.match(f).group(1) for f in files]
    dupes = {n for n in numbers if numbers.count(n) > 1}
    known_dupe = {"0011"}
    unexpected = dupes - known_dupe
    if unexpected:
        die(f"源出现未知编号冲突 {sorted(unexpected)}（超出 ADR-0013 豁免集 0011）"
            "——先修 validate.py 编号唯一性再迁移")

    overrides = load_overrides(
        Path(args.overrides) if args.overrides
        else repo / "scripts" / "migrate_overrides.yaml"
    )
    unknown_ov = set(overrides) - set(files)
    if unknown_ov:
        die(f"overrides.yaml 引用不存在的文件: {sorted(unknown_ov)}")

    staging = Path(args.staging) if args.staging else root / "archive-staging"
    adr_dir = staging / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)

    migrated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entries = []
    stats = {"active": 0, "superseded": 0, "archived": 0}

    for fname in files:
        num = ADR_NAME_RE.match(fname).group(1)
        blob = git(repo, "show", f"{commit}:decisions/{fname}")
        data = blob.encode("utf-8")
        sha = hashlib.sha256(data).hexdigest()

        m = H1_RE.search(blob)
        title = m.group(2) if m else fname
        sm = STATUS_RE.search(blob)
        # decision_status：原文 status 首词（accepted|proposed），括注剥除
        dstatus = "accepted"
        if sm:
            first = re.sub(r"[（(].*", "", sm.group(1)).strip().lower()
            if first in ("accepted", "proposed"):
                dstatus = first

        ov = overrides.get(fname, {})
        lifecycle = ov.get("lifecycle", "active")
        if lifecycle not in LIFECYCLES:
            die(f"{fname}: overrides lifecycle={lifecycle!r} 非法（{LIFECYCLES}）")
        if lifecycle == "superseded" and not ov.get("superseded_by"):
            die(f"{fname}: superseded 必须给 superseded_by")
        if lifecycle != "active" and not ov.get("rationale"):
            die(f"{fname}: 非 active 必须给 rationale")

        entry = [
            f"  - number: {int(num)}",
            f'    title: "{title.replace(chr(34), chr(39))}"',
            f"    file: {fname}",
            f"    lifecycle: {lifecycle}",
            f"    decision_status: {dstatus}",
            f"    archive_path: adr/{fname}",
            f"    content_sha256: {sha}",
        ]
        if lifecycle == "superseded":
            entry.append(f"    superseded_by: {ov['superseded_by']}")
        if lifecycle != "active":
            entry.append(f"    rationale: {ov['rationale']}")
        entries.append("\n".join(entry))
        stats[lifecycle] += 1

        # archive 正本（字节保真——binary 写出，杜绝换行符/编码再加工）
        (adr_dir / fname).write_bytes(data)

        # 墓碑替换（写入工作区 decisions/，同名保留）
        summary = ov.get("summary") or f"{title}"
        tomb = (
            f"# ADR-{num}: {title}（墓碑）\n\n"
            f"- status: {dstatus}\n"
            f"- lifecycle: {lifecycle}\n"
            f"- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/{fname}\n"
            f"- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性"
            f"（adr-required 按文件名校验）。\n\n"
            f"{summary}\n"
        )
        (repo / "decisions" / fname).write_text(tomb, encoding="utf-8", newline="\n")

    index_text = (
        f"# 墓碑索引（W1-C1/ADR-0053）——ADR 编号→状态→archive 路径。\n"
        f"# 机器可读真源：gate adr-required / drift-check §10 经本索引解析 archive 正本；\n"
        f"# 三态 lifecycle 见宪法 §1（active/superseded/archived）；新 ADR 落 archive+此处登记。\n"
        f"# #96（ADR 实质校验）扩展点：entry 可扩展 substantive: {{h1, sections}} 等字段。\n"
        f"version: 1\n"
        f"source_commit: {commit}\n"
        f"migrated_at: {migrated_at}\n"
        f"comment: 墓碑索引（W1-C1/ADR-0053）——ADR 编号→状态→archive 路径；"
        f"新 ADR 落 archive+此处登记\n"
        f"entries:\n" + "\n".join(entries) + "\n"
    )
    (repo / "decisions" / INDEX_NAME).write_text(index_text, encoding="utf-8", newline="\n")

    # ── 报告（PR body 素材）──
    print(f"source_commit: {commit}")
    print(f"entries: {len(files)}  active={stats['active']} "
          f"superseded={stats['superseded']} archived={stats['archived']}")
    print(f"INDEX   : decisions/{INDEX_NAME}")
    print(f"staging : {adr_dir}")
    for fname in files:
        lc = overrides.get(fname, {}).get("lifecycle", "active")
        if lc != "active":
            ov = overrides[fname]
            extra = f" superseded_by={ov.get('superseded_by')}" if lc == "superseded" else ""
            print(f"  {lc:10s} {fname}{extra} — {ov.get('rationale', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
