#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verifier 执照注册校验（W5-C3 .github#226 / ADR-0072 决策 2/6；宪法 §4C）。

执照面规则：
  1. 考试通过才有条目——条目（registry/verifiers/*.yaml）必须能对上成绩存档
     （JSONL，CI-Workflows verifier-exam workflow artifact）：存在 archive_key 行、
     overall_pass=true、judge_id/版本/prompt_hash/冻结哈希逐字段一致。
  2. replay 回放成绩不可注册（judge_mode 必须=api——回放是零真实 LLM 的管道自测，
     不是判官能力证据）。
  3. 标注负债申报必填（annual_hours ≥1 且 status=committed——未配预算不许上岗，
     宪法 §10.4 负债永久）。
  4. 执照默认 shadow（enforcement.veto=false）——升 veto 走宪法 §5 信任门。

用法：
  python3 scripts/verifier-license.py --entry registry/verifiers/<id>.yaml \
      --results <downloaded verifier-exam-results/*.jsonl>
  python3 scripts/verifier-license.py --dir registry/verifiers --results <...>  # 全量
  python3 scripts/verifier-license.py --self-test                             # 内置断言
退出码非 0 = 校验拒绝（validate.yml gate 同款 fail-closed 语义）。
"""
import argparse
import json
import re
import sys
from pathlib import Path

import yaml

KEY_RE = re.compile(r"^(?P<judge>[^@\s]+)@(?P<ver>[^@\s]+)@(?P<ph>[0-9a-f]{12})$")
REQUIRED_TOP = ("license_id", "judge_id", "model_alias", "issued_at", "exam",
                "annotation_budget", "enforcement")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

errors: list = []


def fail(msg: str) -> None:
    errors.append(msg)


def load_results(path: Path) -> dict:
    """成绩存档 JSONL → {archive_key: 最新记录}。"""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        out[rec["archive_key"]] = rec   # 同键多行=多次考试，最新覆盖（历史在行序里）
    return out


def validate_entry(entry: dict, results: dict) -> None:
    eid = entry.get("license_id", "<no-id>")
    for k in REQUIRED_TOP:
        if k not in entry:
            fail(f"{eid}: 缺必填字段 {k}")
    m = KEY_RE.match(entry.get("license_id", ""))
    if not m:
        fail(f"{eid}: license_id 须为 judge_id@exam_version@prompt_hash12 形式")
        return
    if m.group("judge") != entry.get("judge_id"):
        fail(f"{eid}: license_id 的 judge 侧与 judge_id 不一致")

    exam = entry.get("exam") or {}
    # ---- 核心规则：考试通过才有条目（成绩存档对账）----
    key = exam.get("archive_key") or entry.get("license_id")
    rec = results.get(key)
    if rec is None:
        fail(f"{eid}: 成绩存档不存在 archive_key={key}（考试通过才有条目——ADR-0072 决策 2）")
        return
    if rec.get("overall_pass") is not True:
        fail(f"{eid}: 成绩 overall_pass != true（任一分项不过=拒上岗）")
    if rec.get("judge_id") != entry.get("judge_id"):
        fail(f"{eid}: 成绩 judge_id 不符（{rec.get('judge_id')}）")
    if rec.get("exam_version") != exam.get("exam_version"):
        fail(f"{eid}: 成绩 exam_version 不符（{rec.get('exam_version')}）")
    if rec.get("prompt_hash", "")[:12] != (exam.get("prompt_hash") or "")[:12]:
        fail(f"{eid}: 成绩 prompt_hash 不符（prompt 改动即重考）")
    if rec.get("frozen_exam_sha256") != exam.get("frozen_exam_sha256") or \
            not HEX64.match(exam.get("frozen_exam_sha256", "")):
        fail(f"{eid}: 冻结哈希缺失/不符（须=archive manifest freeze_hash，64 hex）")
    # ---- replay 不可注册 ----
    if rec.get("judge_mode") != "api":
        fail(f"{eid}: judge_mode={rec.get('judge_mode')} 的成绩不可注册执照（只认真实判官 api 成绩）")
    if exam.get("judge_mode") not in (None, "api"):
        fail(f"{eid}: exam.judge_mode 只可为 api")
    if exam.get("overall_pass") is not True:
        fail(f"{eid}: exam.overall_pass 必须 true")
    if not exam.get("results_ref"):
        fail(f"{eid}: 缺 results_ref（成绩存档可追溯引用）")

    # ---- 标注负债申报（宪法 §10.4 / ADR-0072 决策 6）----
    bud = entry.get("annotation_budget") or {}
    if not isinstance(bud.get("annual_hours"), int) or bud.get("annual_hours", 0) < 1:
        fail(f"{eid}: annotation_budget.annual_hours 须 ≥1（未配预算不许上岗）")
    if bud.get("status") != "committed":
        fail(f"{eid}: annotation_budget.status 须 committed（申报即承诺）")
    if not bud.get("covers"):
        fail(f"{eid}: annotation_budget.covers 不得为空（预算覆盖面）")

    # ---- shadow 纪律 ----
    enf = entry.get("enforcement") or {}
    if enf.get("veto") is not False:
        fail(f"{eid}: 新发执照必须 enforcement.veto=false（shadow 起步；升 veto 走 §5 信任门）")
    if not enf.get("since"):
        fail(f"{eid}: enforcement.since 缺失")

    rub = entry.get("rubric") or {}
    for k in ("id", "dimensions", "annotation_debt"):
        if k not in rub:
            fail(f"{eid}: rubric 缺 {k}（判据分解+负债申报为 rubric 契约必填）")
    for d in rub.get("annotation_debt") or []:
        if d.get("status") != "insufficient-data" or not d.get("reason") or not d.get("dimension"):
            fail(f"{eid}: rubric.annotation_debt 条目须含 dimension/status=insufficient-data/reason")


def main(argv=None) -> int:
    global errors
    ap = argparse.ArgumentParser(description="verifier 执照注册校验（ADR-0072）")
    ap.add_argument("--entry", help="单个执照条目 yaml")
    ap.add_argument("--dir", default="registry/verifiers", help="执照目录（全量校验）")
    ap.add_argument("--results", help="成绩存档 JSONL（CI artifact 下载后路径）")
    ap.add_argument("--self-test", action="store_true", help="内置正负向断言（零外部依赖）")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    if not args.results:
        print("::error::--results 必填（成绩存档是执照的存在性证明）", file=sys.stderr)
        return 2
    results = load_results(Path(args.results))

    entries = []
    if args.entry:
        entries.append(args.entry)
    else:
        vd = Path(args.dir)
        if not vd.is_dir():
            print(f"::notice::{vd} 不存在——执照面尚无条目（真实判官考试通过后由本脚本校验后登记）")
            return 0
        entries += [str(p) for p in sorted(vd.glob("*.yaml"))]
        if not entries:
            print("::notice::执照面尚无条目（首版无真实判官过考——零真实 LLM 纪律）")
            return 0
    for ep in entries:
        entry = yaml.safe_load(Path(ep).read_text(encoding="utf-8"))
        validate_entry(entry, results)
        print(f"校验 {ep}: {'OK' if not errors else 'REJECTED'}")
    if errors:
        for e in errors:
            print(f"::error::{e}", file=sys.stderr)
        return 1
    return 0


def _rec(**kw):
    base = {"schema": "verifier-exam/result/v1", "archive_key": "jj@1.0.0@abcdef123456",
            "judge_id": "jj", "model_alias": "mm", "prompt_version": "v1",
            "prompt_hash": "abcdef123456" + "0" * 52, "exam_version": "1.0.0",
            "frozen_exam_sha256": "f" * 64, "judge_mode": "api",
            "sampling": {"temperature": 0.0}, "sections": {}, "overall_pass": True,
            "run_id": "r1", "ts": "2026-08-22T00:00:00Z"}
    base.update(kw)
    return base


def _entry(**kw):
    base = {"license_id": "jj@1.0.0@abcdef123456", "judge_id": "jj", "model_alias": "mm",
            "issued_at": "2026-08-22T00:00:00Z",
            "exam": {"archive_key": "jj@1.0.0@abcdef123456", "exam_version": "1.0.0",
                     "prompt_hash": "abcdef123456", "frozen_exam_sha256": "f" * 64,
                     "overall_pass": True, "results_ref": "CI-Workflows run 123 verifier-exam-results",
                     "judge_mode": "api"},
            "annotation_budget": {"annual_hours": 40, "status": "committed",
                                  "covers": ["ai-readability 五维", "校准集回流"]},
            "rubric": {"id": "ai-readability/v1.0.0",
                       "dimensions": ["locatability", "entry_clarity", "module_depth",
                                      "naming_vocabulary", "example_freshness"],
                       "annotation_debt": [{"dimension": "example_freshness",
                                            "status": "insufficient-data", "reason": "示例集未建"}]},
            "enforcement": {"veto": False, "since": "2026-08-22T00:00:00Z"}}
    base.update(kw)
    return base


def self_test() -> int:
    """正负向断言（零外部依赖）：正例过、逐项注入缺陷必须被拒。"""

    def rs(rec):
        return {rec["archive_key"]: rec}

    def exam_of(entry, **kw):
        return dict(entry["exam"], **kw)

    good_entry, good_rec = _entry(), _rec()
    cases = [
        ("正例：真实 api 成绩全对账 → 过", good_entry, rs(good_rec), True),
        ("replay 成绩不可注册", good_entry, rs(_rec(judge_mode="replay")), False),
        ("成绩存档缺键（未考试）", good_entry, {}, False),
        ("overall_pass=false（分项不过）", good_entry, rs(_rec(overall_pass=False)), False),
        ("冻结哈希不符", _entry(exam=exam_of(good_entry, frozen_exam_sha256="a" * 64)),
         rs(good_rec), False),
        ("prompt_hash 不符（prompt 改动即重考）",
         _entry(exam=exam_of(good_entry, prompt_hash="000000000000")), rs(good_rec), False),
        ("无标注预算（未配预算不许上岗）",
         _entry(annotation_budget={"annual_hours": 0, "status": "committed", "covers": ["x"]}),
         rs(good_rec), False),
        ("veto=true 新发（违 shadow 起步）",
         _entry(enforcement={"veto": True, "since": "2026-08-22T00:00:00Z"}), rs(good_rec), False),
        ("license_id 形式非法", _entry(license_id="jj@1.0.0"), rs(good_rec), False),
        ("rubric 负债申报缺失", _entry(rubric={"id": "ai-readability/v1.0.0",
                                               "dimensions": ["locatability"]}), rs(good_rec), False),
    ]
    global errors
    ok = True
    for name, entry, results, expect_ok in cases:
        errors = []
        validate_entry(entry, results)
        passed = (not errors) == expect_ok
        ok = ok and passed
        print(f"{'PASS' if passed else 'FAIL'}: {name}" + ("" if passed else f" → {errors}"))
    print("self-test:", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
