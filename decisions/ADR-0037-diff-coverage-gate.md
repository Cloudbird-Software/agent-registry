# ADR-0037: diff coverage 门槛——PR 变更行覆盖率门禁（P2-3）

- status: accepted（2026-08-20）
- 背景: .github issue #81（自动合并计划）§4.1 工作卡 #88（P2-3 diff coverage 门槛）
- 关联: .github governance/policy/testing.yaml（diff_coverage 段）、CI-Workflows
  scripts/diff-coverage.py、CI-Workflows .github/workflows/diff-coverage.yml、
  ADR-0013（adr-required）、ADR-0021（GITHUB_TOKEN 读公开仓）、ADR-0032（skipped≠success）

## 背景

无人 review 时（#81 自动合并计划），"测试还在跑且绿"不等于"新代码被测过"。
agent 最经济的通过策略是加代码不加测试。全局覆盖率门槛挡不住这一类：分母是
全量代码行，一个 90% 覆盖率的仓库顺手合入 200 行无测试代码后全局只掉零点几
个百分点，门槛照绿——**大 PR 稀释小增量**。diff coverage 只问一个问题：
这个 PR 新增/修改的行，有没有被测试执行到。分母只有本次变更行，全局覆盖率
再高也稀释不了（#88 T3 稀释攻击负向测试即验证此点）。

与 testing.yaml X-01 的关系：X-01 拒绝的是 `coverage_threshold_gate`（**全局**
覆盖率门槛，理由"数字可游戏"——往项目塞无关测试即可拉高分母）。本 ADR **不翻
案 X-01**：全局口径继续拒绝；diff 口径分母锁定为本次变更行，塞无关测试拉不动
本 PR 的分子分母，X-01 的攻击面不适用。故另立 T-12（active_now），X-01 补注
说明边界。

## 决策

1. **口径**：PR 变更行 = `git diff -M -U0 $(git merge-base origin/<base> HEAD) HEAD`
   的 unified diff 新增行（含修改行——修改行在 diff 中呈现为 -旧/+新 对，取
   +新；删除行不计）。diff coverage = 变更行中被测试执行到的行数 / 参与计量的
   变更行数。语言栈×覆盖率数据格式（受管仓语言盘点，选型优先现成格式而非现成
   工具——diff-cover 等绑单一生态且需引入新供应链面）：
   - node（template-service 等）：vitest `--coverage` 产出的 **lcov**
     （`coverage/lcov.info`）或 istanbul JSON（`coverage/coverage-final.json`）；
   - python（agent-platform / AI_Web_School）：pytest-cov `--cov-report=xml`
     产出的 **Cobertura XML**（coverage.xml）；
   - go（mutual）：`go test -coverprofile=coverage.out` 产出的 **go covprofile**。
   交集算法统一：变更行集 ∩ 覆盖行集；一行级精确计量。
2. **工具**：CI-Workflows `scripts/diff-coverage.py`，**stdlib-only**（四格式
   解析 lcov / istanbul JSON / Cobertura XML / go covprofile；policy 解析用
   pip 哈希锚定的 PyYAML，沿用 .github requirements-gate.txt 同款钉法）。理由：
   多语言仓统一口径（现成工具各绑单一生态）；org 供应链钉哈希政策下不新增
   三方包；#88 T6 要求 fixture 级精确验证（±0.1%），自研可测。工具自带
   `--self-test`（预标注 fixture 三组：等值边界、稀释攻击、豁免与低于阈值），
   **每次执法运行前置执行**——工具自身算错比漏检更糟。
3. **阈值与边界语义**：默认 **80%**，真源 `.github governance/policy/testing.yaml`
   新增 `diff_coverage:` 段（threshold_pct）。边界（#88 T4）：covered/total
   **≥ 80.0 绿（等值绿）；< 80.0 红**（79.9 即红）。按仓覆盖允许（更严或更宽），
   但覆盖值必须登记在 policy `repo_overrides`——caller workflow input 显式声明
   的阈值与登记值不一致即红：**阈值不得由业务仓 PR 自行放宽**。
4. **豁免清单**：文档/配置/生成代码按扩展名 + 文件名 + 路径前缀三类 glob 声明
   于 policy `diff_coverage.exempt_*`（默认：.md/.json/.yaml/.sql 等、
   Makefile/Dockerfile/CODEOWNERS 等、vendor//golden//baml_client/ 等）。
   豁免行不计入分母。真源在 .github（C1 路径：governance/ 变更触发 adr-required
   + owner-only review）——**业务仓 PR 作者无权扩大豁免**；豁免清单本身被修改
   必须走 ADR（gate.yml adr-required 机器拦截，#88 T5 后半）。
5. **fail-closed**：以下情形一律红，不得静默绿——(a) 存在非豁免变更行但覆盖率
   数据缺失/工件不存在（"没测过"≠"测了没覆盖"）；(b) 覆盖率数据存在但不可
   解析；(c) policy 拉取失败或缺 diff_coverage 段；(d) 显式阈值与登记不符。
   豁免行/无计量数据的行（如 istanbul 无语句的纯语法行）不计分母——语义为
   "该行无覆盖率数据"且其文件已有覆盖率数据覆盖，与 (a) 的"整仓零数据"区分。
6. **接入形态**：CI-Workflows 新 reusable workflow `diff-coverage.yml`，业务仓
   `ci.yml` 的 gate needs 链接入（`needs: [..., diff-coverage]`）；仅 PR 事件
   执法，push 事件由 caller 按 ADR-0032 在 EXPECTED_SKIP 登记结构性跳过。
   门禁三要素全部来自被审 PR 改不动的位置（#81 §3.3 原则）：workflow 本体
   （caller 钉 ref 引用）、执法工具（从本 workflow 同 ref checkout CI-Workflows，
   不取 caller 仓内副本）、阈值与豁免（读 .github main 的 policy）。job 权限
   contents:read（checkout caller 全历史求 merge-base + GITHUB_TOKEN 读公开
   .github policy，ADR-0020/0021 先例）；不注入 org secret。
7. **验收测试映射**（#88）：T1 低于阈值红+未覆盖行清单（工具输出逐文件行号）；
   T2 达标绿；T3 稀释攻击红（fixture2 即此形态的单元级固化）；T4 边界语义进
   policy 注释+fixture1 等值绿；T5 豁免清单（fixture3 含豁免文件不计分母）+
   豁免变更走 ADR；T6 三组预标注 fixture `--self-test` 精确断言（每次执法前置）。
   T1/T2/T3 的 PR 级端到端注入须待 caller 接线（P2-1/P2-2 同批）后在业务仓执行。

## 后果

- "顺手加 200 行无测试代码"从全局覆盖率的统计噪声变为即时红——自动合并的第
  三道语义门（继 #86 测试篡改检测、#87 抑制标记预算之后）。
- 业务仓接入成本：make test 产出四格式之一（node 仓 vitest --coverage 现成；
  python 仓 Makefile 补 `--cov-report=xml`；go 仓补 `-coverprofile`）+ gate
  needs 链两行——随 P2-1/P2-2 批次落地，不在本 ADR 范围。
- 运行成本：每 PR 一次 diff 解析+交集（纯 CPU，秒级），timeout 5min 预算内。
- X-01 维持拒绝（全局口径）；未来若要恢复全局覆盖率门槛须新 ADR 翻案。
- 豁免清单初版为最小集，按仓扩展（如 AI_Web_School alembic 迁移路径）走
  本 ADR 的修订或后继 ADR——每次豁免扩大都缩小门的覆盖面，应保持高摩擦。
