# ADR-0039: 依赖供应链 policy 落地——dep-review 从"跑了"升级为有具体 policy（P2-5）

- status: accepted（2026-08-20）
- 背景: .github issue #81（自动合并计划）§4.1/§5 工作卡 #90（P2-5 依赖供应链 policy）
- 关联: ADR-0026（dep-review 许可证豁免透传）、ADR-0018（supply_chain 风险姿态）、
  ADR-0021（CI 门禁体系）、ADR-0032（gate aggregator 严格化——本卡新增 job 经
  caller `deps` job 汇聚，不改 caller gate）、ADR-0028（Go 基线）、
  .github governance/policy/languages.yaml dependency_policy（approval_required 域）

## 背景

dep-review 此前只有 org deny 清单（AGPL-3.0/GPL-3.0/SSPL-1.0）+ 高危漏洞阻断：
"跑了"但没有针对 LLM 供应链攻击面的判据。真实威胁（#81 §5）：agent 幻觉包名 →
攻击者抢注（typosquat/slopsquat）→ 下次安装即中招。公开仓库，manifest/lockfile
新增条目即攻击面（risk_posture: supply_chain），此前零门禁。四类缺口（#90 步骤
1-4）：

1. 许可证是 deny 名单而非 allow 名单——未列举的许可证默认放行（fail-open）。
2. 新增依赖无包龄/流行度判据——发布 1 天、零下载、单维护者的抢注包与十年
   成熟包同权通过。
3. postinstall/构建期脚本（npm `postinstall`、PyPI sdist `setup.py`）在安装时
   以依赖作者身份执行任意代码，无审批要求。
4. lockfile 与 manifest 一致性依赖各仓自觉——手改 lockfile、忘更新 lockfile
   在非 frozen 安装模式下静默通过。

## 决策

1. **policy 单一真源落 CI-Workflows `policy/dependency-supply-chain.yaml`**。
   dep-review 运行时从被调用 workflow 自身 ref（`github.workflow_ref` 解析）
   checkout 本仓读取——policy、判定脚本（`scripts/dep-supply-chain-check.py`）、
   workflow 定义三者**同 ref 原子发布**：调用方 PR 改不到 CI-Workflows，本仓 PR
   无法只改其一而不同步其余（防削弱，同 #81 §3.3 思路）。阈值修订 = C1 变更
   （须引用 ADR）。卡内原提及 `.github governance/policy/`：独立落 .github 会与
   gate 判定逻辑形成两个可漂移副本且丧失同 ref 原子性；对账改为后续卡从
   drift-check 拉取本文件校验（本卡不动 expected-state.json）。

2. **许可证白名单（拒绝式）**：dependency-review-action 改用 `allow-licenses`
   （deny-by-default），全量来自 policy 文件（MIT/Apache-2.0/BSD-2-Clause/
   BSD-3-Clause/ISC/0BSD/Zlib/BSL-1.0/Python-2.0/MPL-2.0/Unlicense/CC0-1.0/
   BlueOak-1.0.0/BSD-2-Clause-Patent/PostgreSQL 等 OSI 宽松系）。不在白名单=红。
   原 deny 清单（AGPL/GPL/SSPL）语义被白名单包含（不在列表即拒），删除。
   ADR-0026 PURL 精确豁免通道（`allow-dependencies-licenses` 输入）原样保留。

3. **包龄与流行度**（dep-review 新增 `supply-chain` job，逐**新增**依赖查
   registry；既有依赖 minor/patch 更新不在本域，见 languages.yaml
   dependency_policy 划界）：
   - 包龄取包**首次发布**时间：npm packument `time.created`；PyPI releases 最早
     `upload_time`；Go `proxy.golang.org/<mod>/@v/<ver>.info` 的 `Time`。
   - 包龄 < `min_age_days: 90` → **硬红**（幻觉抢注包直接防线，ADR 引用不豁免）。
   - 周下载量 < `min_weekly_downloads: 100` → 红，PR 引用 ADR-NNNN 可过（需 ADR）。
   - 维护者数=1 且无组织背书 → 红，需 ADR（仅 npm 可机器判定，PyPI 无
     maintainers API——policy 显式声明各判据适用面，Go 无公开下载量 API 同理）。
   - **包不存在**（registry 404）→ 硬红，错误信息明确"包不存在于 registry"——
     幻觉包典型形态，不得误报为其他错误（#90 T2 第二断言）。
   - registry 不可达（网络错/超时）→ 红（fail-closed：无人值守下 fail-open 的
     代价高于误拦）。
   - first-party 豁免：npm `@cloudbird-software/*` scope、Go `github.com/
     Cloudbird-Software/*` 前缀跳过包龄/下载量/维护者/脚本判据（组织自有包天然
     年轻零下载）；许可证检查不豁免。

4. **postinstall/构建期脚本 → 需 ADR**：新增 npm 依赖锁定版本 manifest 含
   `preinstall`/`install`/`postinstall` 脚本，或新增 PyPI 依赖锁定版本仅有 sdist
   无 wheel（安装即执行 `setup.py`）→ 红，PR 引用 ADR-NNNN 可过（人审留痕）。

5. **lockfile 一致性（frozen/immutable）**：
   - dep-review 增**静态一致性校验**（名/精确版本级，安装步之前拦截）：npm
     `package.json` ↔ `package-lock.json` 根依赖；`go.mod` require ↔ `go.sum`
     双哈希行；`pyproject.toml` dependencies ↔ `uv.lock`。不一致即红。
   - 深度（哈希级）校验执法点在各仓安装命令（`make setup`）：`npm ci` /
     `pip install --require-hashes` / `uv sync --locked` / `go mod verify`——
     required_mode 矩阵落 policy 可对账。各仓 frozen 改造按 #90 约定可拆子任务
     （现状：npm 三仓 `npm ci`、AI_Web_School `--require-hashes` 已 frozen；
     agent-platform `uv sync` 待补 `--locked`，见后果）。

6. **阈值消费证明进 CI（#90 T6 单元级）**：`--self-test` 离线断言同一成熟依赖在
   `min_age_days: 90` 判绿、`10000` 判红——证明判定消费 policy 阈值而非硬编码；
   self-test + policy schema 校验进 CI-Workflows hygiene job（每 PR 跑）。

7. **caller 侧零改动接入**：新增 job 都在 dep-review workflow 内部，调用方 `deps`
   job 结果=被调 workflow 全 job 汇聚（ADR-0032 严格断言在 caller gate 原样生效）。
   调用方生效需 bump `@ref` pin（fixture 验证 T1-T5 时进行）。

## 后果

- dep-review 从告警式升级为拒绝式：非白名单许可证、<90 天新包、不存在包名一律
  硬红；低下载/单维护者/install 脚本有 ADR 逃生门（人审留痕，非静默放行）。
- 白名单比原 deny 名单严格：冷门/弱 copyleft 许可证（LGPL 系等）默认红，误报走
  ADR-0026 PURL 豁免或 ADR 引用——不再静默通过。
- npm/PyPI/proxy.golang.org 成为合并路径的运行时依赖，不可达=fail-closed 红；
  接受该可用性代价（供应链门禁降级=fail-open 攻击面）。
- agent-platform `uv sync` 需补 `--locked`（哈希级 frozen 拼图最后一块）；其余仓
  安装命令已 frozen。#90 T4 验收以安装步失败为准。
- 后续卡（#98 SLI 面板）可消费本 gate 违规分类计数（not_found/age/downloads/
  maintainer/scripts/lockfile）作为供应链熵增指标。
