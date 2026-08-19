#!/usr/bin/env python3
"""snapshot.py —— 声明面规范化快照（治理差分测试的基底，ADR-0021 决策 9）。

把全部声明文件（standards/*.yaml + registry/**）解析为数据后做规范化投影：
  {相对路径: 解析后的数据}，键排序、UTF-8、紧凑分隔符——渲染确定，
  同一棵树任意次运行字节级一致（差分测试的前提）。

用法：
  python3 scripts/snapshot.py                 # 写入 tests/golden/declarations.json
  python3 scripts/snapshot.py --check         # 与 golden 比对，不一致 exit 1（CI 差分门禁）

差分语义：声明文件的任何语义变化必然落入快照 diff（注释级变化不落入——快照测
"声明的世界"的数据面，注释属散文层）。PR 改声明必须同步再生成 golden，评审看到
的 golden diff = 该 PR 对声明语义面的完整影响清单——"声明变更的可审差分"。
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden" / "declarations.json"

# 快照覆盖面 = 声明层全部（standards + registry；schemas 是声明引用的契约，一并纳入）
SCOPES = ("standards", "registry")


def build_snapshot() -> dict:
    snap: dict = {}
    for scope in SCOPES:
        for p in sorted((ROOT / scope).rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(ROOT).as_posix()
            if p.suffix in (".yaml", ".yml"):
                data = yaml.safe_load(p.read_text(encoding="utf-8"))
            elif p.suffix == ".json":
                data = json.loads(p.read_text(encoding="utf-8"))
            else:
                continue  # SKILL.md 等：正文为提示词非声明数据，frontmatter 由 validate 消费
            if data is None:
                data = {"__empty__": True}
            snap[rel] = data
    return snap


def normalize(obj):
    """递归规范化：dict 键一律转 str（YAML 1.1 的 on/off/yes/no 会被解析为布尔键——
    键类型混杂使 sort_keys 崩溃；转 str 后 'True' 与 'on' 的语义混排不影响差分正确性：
    同一棵树的解析结果恒定，差分只对树变化敏感）。"""
    if isinstance(obj, dict):
        return {str(k): normalize(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    if isinstance(obj, list):
        return [normalize(x) for x in obj]
    if isinstance(obj, tuple):
        return [normalize(x) for x in obj]
    return obj


def render(snap: dict) -> str:
    return json.dumps(normalize(snap), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="与 golden 比对（不一致 exit 1）")
    args = ap.parse_args()

    snap = build_snapshot()
    if not snap:
        print("SNAPSHOT FAIL: 声明面为空（standards/ + registry/ 无可解析文件）")
        return 1
    rendered = render(snap)

    if args.check:
        if not GOLDEN.is_file():
            print(f"SNAPSHOT FAIL: golden 缺失 {GOLDEN}——先运行 python3 scripts/snapshot.py 生成并提交")
            return 1
        golden = GOLDEN.read_text(encoding="utf-8")
        if golden == rendered:
            print(f"SNAPSHOT OK: 声明面与 golden 一致（{len(snap)} 个声明文件）")
            return 0
        # 定位差异文件（评审导航）
        g = json.loads(golden)
        changed = sorted(
            set(g) ^ set(snap)
            | {k for k in set(g) & set(snap) if render({k: g[k]}) != render({k: snap[k]})}
        )
        print("SNAPSHOT FAIL: 声明面与 golden 不一致（差分=本 PR 的声明语义变更面，"
              "须有意更新：python3 scripts/snapshot.py && git add tests/golden/declarations.json")
        for c in changed:
            mark = "+" if c not in g else ("-" if c not in snap else "±")
            print(f"  {mark} {c}")
        return 1

    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN.write_text(rendered, encoding="utf-8")
    print(f"SNAPSHOT: 写入 {GOLDEN.relative_to(ROOT)}（{len(snap)} 个声明文件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
