"""verifier-license.py 元验证（W5-C3 .github#226 / ADR-0072——注册门自身必须被测）。

validate 的对象=scripts/verifier-license.py（执照注册校验器）。套件提供回归基线：
  - 正向：合法条目+真实 api 成绩存档必须放行。
  - 负向：逐项注入缺陷（replay 成绩/未考试/分项不过/哈希不符/无预算/veto 越权
    /键形式非法）必须被拒。
  - CLI：--results 缺失 exit 2（执照的存在性证明不可缺省）。
运行：python -m pytest tests/ -v（governance-tests.yml regression job 内执行）。
"""
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "verifier-license.py"

GOOD_REC = {
    "schema": "verifier-exam/result/v1",
    "archive_key": "judge-x@1.0.0@0123456789ab",
    "judge_id": "judge-x", "model_alias": "glm-4.5-air", "prompt_version": "v1",
    "prompt_hash": "0123456789ab" + "0" * 52, "exam_version": "1.0.0",
    "frozen_exam_sha256": "f" * 64, "judge_mode": "api",
    "sampling": {"temperature": 0.0, "seed": 42}, "sections": {}, "overall_pass": True,
    "run_id": "42", "ts": "2026-08-22T00:00:00Z",
}

GOOD_ENTRY = {
    "license_id": "judge-x@1.0.0@0123456789ab",
    "judge_id": "judge-x", "model_alias": "glm-4.5-air",
    "issued_at": "2026-08-22T00:00:00Z",
    "exam": {"archive_key": "judge-x@1.0.0@0123456789ab", "exam_version": "1.0.0",
             "prompt_hash": "0123456789ab", "frozen_exam_sha256": "f" * 64,
             "overall_pass": True,
             "results_ref": "CI-Workflows run 42 verifier-exam-results",
             "judge_mode": "api"},
    "sampling": {"temperature": 0.0, "seed": 42},
    "annotation_budget": {"annual_hours": 40, "status": "committed",
                          "covers": ["ai-readability 五维", "校准集回流"]},
    "rubric": {"id": "ai-readability/v1.0.0",
               "dimensions": ["locatability", "entry_clarity", "module_depth",
                              "naming_vocabulary", "example_freshness"],
               "annotation_debt": []},
    "enforcement": {"veto": False, "since": "2026-08-22T00:00:00Z"},
}


def run_cli(entry, rec, tmp_path):
    ep = tmp_path / "e.yaml"
    ep.write_text(yaml.safe_dump(entry, allow_unicode=True), encoding="utf-8")
    rp = tmp_path / "r.jsonl"
    rp.write_text(json.dumps(rec) + "\n" if rec else "", encoding="utf-8")
    return subprocess.run([sys.executable, str(SCRIPT), "--entry", str(ep),
                           "--results", str(rp)], capture_output=True, text=True, timeout=60)


def mutated_entry(**kw):
    import copy
    e = copy.deepcopy(GOOD_ENTRY)
    for k, v in kw.items():
        if isinstance(v, dict) and isinstance(e.get(k), dict):
            e[k].update(v)
        else:
            e[k] = v
    return e


def mutated_rec(**kw):
    import copy
    r = copy.deepcopy(GOOD_REC)
    r.update(kw)
    return r


def test_positive_real_api_result_registers(tmp_path):
    r = run_cli(GOOD_ENTRY, GOOD_REC, tmp_path)
    assert r.returncode == 0, r.stderr


def test_replay_result_rejected(tmp_path):
    r = run_cli(GOOD_ENTRY, mutated_rec(judge_mode="replay"), tmp_path)
    assert r.returncode == 1 and "不可注册" in r.stderr


def test_missing_archive_rejected(tmp_path):
    r = run_cli(GOOD_ENTRY, None, tmp_path)   # 空成绩存档=未考试
    assert r.returncode == 1 and "成绩存档不存在" in r.stderr


def test_failed_exam_rejected(tmp_path):
    r = run_cli(GOOD_ENTRY, mutated_rec(overall_pass=False), tmp_path)
    assert r.returncode == 1 and "overall_pass" in r.stderr


def test_prompt_hash_mismatch_rejected(tmp_path):
    r = run_cli(mutated_entry(exam={"prompt_hash": "ffffffffffff"}), GOOD_REC, tmp_path)
    assert r.returncode == 1 and "prompt_hash" in r.stderr


def test_no_annotation_budget_rejected(tmp_path):
    r = run_cli(mutated_entry(annotation_budget={"annual_hours": 0, "status": "committed",
                                                 "covers": ["x"]}), GOOD_REC, tmp_path)
    assert r.returncode == 1 and "annual_hours" in r.stderr


def test_veto_shortcut_rejected(tmp_path):
    r = run_cli(mutated_entry(enforcement={"veto": True, "since": "2026-08-22"}), GOOD_REC, tmp_path)
    assert r.returncode == 1 and "veto" in r.stderr


def test_cli_requires_results_fail_closed():
    r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 2 and "--results" in r.stderr


def test_builtin_selftest_green():
    r = subprocess.run([sys.executable, str(SCRIPT), "--self-test"],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "self-test: OK" in r.stdout


def test_schema_file_valid_and_registered():
    import json as _json
    sch = _json.loads((ROOT / "registry" / "schemas" / "verifier-license.json").read_text(encoding="utf-8"))
    assert sch["type"] == "object"
    req = sch["required"]
    assert all(k in sch["properties"] for k in req)   # validate.py 语法门（ADR-0022 D-5）
    # 执照核心语义进 schema：真实判官 + shadow 起步 + 负债申报
    assert sch["properties"]["exam"]["properties"]["judge_mode"]["enum"] == ["api"]
    assert "annotation_budget" in req and "enforcement" in req
