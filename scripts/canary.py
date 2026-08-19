#!/usr/bin/env python3
"""canary.py —— 治理金丝雀（无凭据，消费四仓公开声明与线上可观察面。ADR-2021 决策 9）。

定位（与既有防线的分工）：
  - drift-check（.github，admin token）：线上配置 vs 落盘期望的**权威对账**。
  - 本 canary（agent-registry，零凭据）：周期性验证"治理体系公开可观察面"仍满足
    声明的不变量——任何一仓的意外变动（指针漂移/防线被删/声明与公开面断裂）在
    无 admin token 的环境下也可见。fail-closed：网络失败=失败，不静默跳过。

检查项（全部机器可判定）：
  C1 GM-1 频率口径：governance-drift.yml 为小时级 cron，且 GOVERNANCE.yaml 无
     'daily 03:00' 陈旧口径残留。
  C2 App 名一致性：expected-state.json 的 github_app.name 与全部 agent 声明的
     credential.github_app 完全一致（红队实证曾存在 cloudbrid/cloudbird 双写）。
  C3 组织地图：REPOS.yaml active 仓全部存在且 public；线上仓全部已申报；
     planned 仓不冒充存在。
  C4 供应链入口：template-service 与 CI-Workflows 的 CI 引用本组织 reusable
     workflow 且为版本指针（@vN，非 @main）；三治理仓 gate 含 adr-required；
     template-service gate 聚合 hygiene/check/deps。
  C5 规则集声明自洽：main-protection 落盘 require_code_owner_review=false
     （SC-3 automerge 前提，ADR-0021）；required check=gate；codeql-gate 豁免 .github。
  C6 动作钉扎：各仓 workflow 的 actions 引用一律 40-hex SHA 锚定（组织自身
     reusable workflow 引用允许 @vN 大版本指针——CI-Workflows 版本策略）。
  C7 脚本防线在位：drift-check.sh 含 §8 直推/§9 admin 唯一/§10 ADR 实体性段落。

用法：python3 scripts/canary.py  （退出码非 0 = 金丝雀死亡——治理流程测试回路红灯）
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ORG = "Cloudbird-Software"
REPOS = ("agent-registry", ".github", "CI-Workflows", "template-service")
UA = {"User-Agent": "cloudbird-governance-canary"}
RAW = "https://raw.githubusercontent.com"
API = "https://api.github.com"

errors: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def fetch_text(url: str, retries: int = 2) -> str:
    last = None
    for _ in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2)
    raise RuntimeError(f"fetch 失败（fail-closed）: {url}: {last}")


def fetch_json(url: str):
    return json.loads(fetch_text(url))


def raw(repo: str, path: str, ref: str = "main") -> str:
    return fetch_text(f"{RAW}/{ORG}/{repo}/{ref}/{path}")


# ── C1 频率口径 ──────────────────────────────────────────────
def check_c1() -> None:
    wf = raw(".github", ".github/workflows/governance-drift.yml")
    if "0 * * * *" not in wf:
        fail("C1: governance-drift.yml 缺小时级 cron '0 * * * *'（GM-4 声明 hourly）")
    gov = raw(".github", "governance/GOVERNANCE.yaml")
    if "daily 03:00" in gov:
        fail("C1: GOVERNANCE.yaml 残留 'daily 03:00' 陈旧频率口径（实现已 hourly——声明漂移）")


# ── C2 App 名一致性 ──────────────────────────────────────────
def check_c2() -> None:
    expected = json.loads(raw(".github", "governance/expected-state.json"))
    app = expected.get("github_app", {}).get("name")
    if not app:
        fail("C2: expected-state.json 缺 github_app.name")
        return
    listing = fetch_json(f"{API}/repos/{ORG}/agent-registry/contents/registry/agents")
    names = [x["name"] for x in listing if x["type"] == "file" and x["name"].endswith(".yaml")]
    if not names:
        fail("C2: agent-registry registry/agents 清单为空（fail-closed）")
    for n in names:
        a = yaml.safe_load(raw("agent-registry", f"registry/agents/{n}"))
        got = (a.get("credential") or {}).get("github_app")
        # 只校验已声明者：写仓库的 agent 走 App；只读/无 GitHub 面（researcher 等）可不声明
        if got is not None and got != app:
            fail(f"C2: agent 声明 {n} credential.github_app={got!r} ≠ expected-state {app!r}（App 名双源漂移）")


# ── C3 组织地图 ──────────────────────────────────────────────
def check_c3() -> None:
    m = yaml.safe_load(raw(".github", "governance/REPOS.yaml"))
    declared = {r["name"]: r for r in m.get("repos", []) if isinstance(r, dict)}
    live = {r["name"]: r for r in fetch_json(f"{API}/orgs/{ORG}/repos?per_page=100")
            if isinstance(r, dict)}
    if len(live) >= 100:
        fail("C3: org 仓清单达到单页上限（>=100），canary 单页拉取不完整——改分页或缩编")
    for name, spec in declared.items():
        if spec.get("status") == "active":
            if name not in live:
                fail(f"C3: REPOS.yaml active 仓 {name} 线上不存在")
            elif live[name].get("private"):
                fail(f"C3: REPOS.yaml active 仓 {name} 为 private（违反 ADR-0020 全仓公开）")
    for name in live:
        if name not in declared:
            fail(f"C3: 线上仓 {name} 未在 REPOS.yaml 申报（GM-4）")


# ── C4 供应链入口 ────────────────────────────────────────────
def check_c4() -> None:
    tmpl_ci = raw("template-service", ".github/workflows/ci.yml")
    for w in ("hygiene.yml", "check.yml", "dep-review.yml"):
        if f"Cloudbird-Software/CI-Workflows/.github/workflows/{w}@v" not in tmpl_ci:
            fail(f"C4: template-service ci.yml 未引用 CI-Workflows/{w}@vN（CI-1 聚合防线缺口）")
    checks = {
        ".github": raw(".github", ".github/workflows/gate.yml"),
        "CI-Workflows": raw("CI-Workflows", ".github/workflows/ci.yml"),
        "agent-registry": raw("agent-registry", ".github/workflows/validate.yml"),
    }
    for repo, text in checks.items():
        if "adr-required" not in text:
            fail(f"C4: {repo} 的 gate 工作流缺 adr-required 步骤（C1 治理路径机器检查）")
    if "gate" not in tmpl_ci:
        fail("C4: template-service ci.yml 缺 gate 聚合 job（BP-2 required check）")


# ── C5 规则集声明自洽 ────────────────────────────────────────
def check_c5() -> None:
    mp = json.loads(raw(".github", "governance/rulesets/main-protection.json"))
    pr_rules = [r for r in mp.get("rules", []) if r.get("type") == "pull_request"]
    if not pr_rules:
        fail("C5: main-protection 落盘缺 pull_request 规则")
    else:
        p = pr_rules[0].get("parameters", {})
        if p.get("require_code_owner_review") is not False:
            fail("C5: main-protection require_code_owner_review != false"
                 "（单人 CODEOWNERS+owner review 要求=一切合并只能 admin bypass，SC-3 automerge 死锁——ADR-0021）")
        if p.get("required_approving_review_count") != 0:
            fail("C5: main-protection required_approving_review_count != 0（一人公司自批无效——声明的 0 才与现实一致）")
    rsc = [r for r in mp.get("rules", []) if r.get("type") == "required_status_checks"]
    ctxs = [c.get("context") for r in rsc for c in r.get("parameters", {}).get("required_status_checks", [])]
    if ctxs != ["gate"]:
        fail(f"C5: main-protection required checks={ctxs} != ['gate']（BP-2）")
    cg = json.loads(raw(".github", "governance/rulesets/codeql-gate.json"))
    excl = (((cg.get("conditions") or {}).get("repository_name") or {}).get("exclude")) or []
    if ".github" not in excl:
        fail("C5: codeql-gate 未豁免 .github（治理仓无代码扫描面——豁免口径漂移）")


# ── C6 动作钉扎 ──────────────────────────────────────────────
SHA_RE = re.compile(r"uses:\s*([^\s@]+)@([0-9a-f]{40})\s")
TAGGED_RE = re.compile(r"uses:\s*([^\s@]+)@v[0-9]+\s")


def check_c6() -> None:
    targets = {
        ".github": [".github/workflows/gate.yml", ".github/workflows/governance-drift.yml",
                    ".github/workflows/scorecard.yml"],
        "CI-Workflows": [".github/workflows/ci.yml", ".github/workflows/check.yml",
                         ".github/workflows/hygiene.yml", ".github/workflows/dep-review.yml",
                         ".github/workflows/release.yml", ".github/workflows/scorecard.yml"],
        "template-service": [".github/workflows/ci.yml", ".github/workflows/automerge.yml",
                             ".github/workflows/scorecard.yml"],
        "agent-registry": [".github/workflows/validate.yml"],
    }
    uses_re = re.compile(r"uses:\s*(\S+)")
    for repo, files in targets.items():
        for f in files:
            try:
                text = raw(repo, f)
            except RuntimeError:
                fail(f"C6: {repo}/{f} 拉取失败（fail-closed）")
                continue
            for m in uses_re.finditer(text):
                ref = m.group(1)
                action, _, ver = ref.rpartition("@")
                if action.startswith(f"{ORG}/CI-Workflows/"):
                    if not re.fullmatch(r"v[0-9]+", ver):
                        fail(f"C6: {repo}/{f} 组织 reusable workflow 引用 {ref} 非 @vN 版本指针")
                    continue
                if not re.fullmatch(r"[0-9a-f]{40}", ver):
                    fail(f"C6: {repo}/{f} action 引用 {ref} 未按 40-hex SHA 钉扎（ADR-0011 立场）")


# ── C7 脚本防线在位 ──────────────────────────────────────────
def check_c7() -> None:
    dc = raw(".github", "governance/drift-check.sh")
    for marker in ("---------- 8", "---------- 9", "---------- 10"):
        if marker not in dc:
            fail(f"C7: drift-check.sh 缺 {marker} 段（直推/admin/ADR 实体性防线被删？）")


def main() -> int:
    for fn in (check_c1, check_c2, check_c3, check_c4, check_c5, check_c6, check_c7):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            fail(f"{fn.__name__}: 执行异常（fail-closed）: {e}")
    if errors:
        print(f"CANARY FAIL ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("CANARY OK: 四仓公开治理面不变量全部成立（C1-C7）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
