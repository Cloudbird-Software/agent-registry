# ADR-0035: 测试篡改检测门 test-integrity（P2-1）

- status: accepted（2026-08-20）
- 背景: .github issue #81（自动合并计划）§4.1 工作卡 #86（P2-1 测试篡改检测门）
- 关联: CI-Workflows scripts/test-integrity.sh 与 .github/workflows/test-integrity.yml、
  CI-Workflows scripts/test-integrity-fixtures/（T8 单元级 fixture 自检）、
  .github governance/policy/testing.yaml#test_integrity（规则/阈值声明）、
  ADR-0016（adr-required 机制——逃生门复用其词边界+存在性校验模型）、
  ADR-0032（gate aggregator 严格断言——新门接入范式）、ADR-0021（C1 治理路径）

## 背景

无人 review 时，agent 最经济的通过策略是改判据而不是改代码（#81 §4.1）。测试篡改
是 agent 最经典的作弊路径，四类形态：

1. **删除红测试**：把失败的测试文件直接删掉；
2. **断言改松**：断言数量净下降（5 个改 3 个）；
3. **抑制标记**：新增 skip / xfail / only / t.Skip / pytest.mark.skip；
4. **期望值改写**：只改测试期望值不改实现——把判据改成现状。

现有 gate（hygiene / adr-required / gitleaks / zizmor / check）全部不设防这一类：
它们校验"代码跑得过"，不校验"判据没被换"。auto-merge 全开后（Phase 1，ADR-0029/
0031/0032/0034），这是自动合并安全性的**第一必需门**。

## 决策

1. **新增 test-integrity 门**（regex 级、语言无关；AST 级解析为后续增强，不在本卡
   范围），四条规则，命中即红：
   - TI-R1 测试文件删除（diff 中测试路径出现真实删除；rename 保留内容不算删除）；
   - TI-R2 测试文件断言计数净下降（assert/expect/require/t.Error 等按 policy 声明
     的模式；全 PR 净值 < 0 即红——按净额判定，测试在文件间迁移不受影响）；
   - TI-R3 新增抑制标记（skip/xfail/only/t.Skip/mark.skip 等出现在新增行）；
   - TI-R4 期望值改写嫌疑（测试文件存在删改行 + 零实现文件变更）——严格度由
     policy 声明，缺省 require_adr（可调为不可豁免的 red）。
2. **fail-closed**：base/head SHA 不可解析、diff 生成失败、policy 拉取失败、逃生门
   需要的 ADR 清单拉取失败——一律红，绝不静默放行（"检测器读不到=红"）。
3. **逃生门**：规则命中后，PR title/body 引用 ADR-NNNN 可豁免（复用 adr-required
   机制：`\bADR-NNNN\b` 词边界 + agent-registry/decisions 存在性校验，防幽灵 ADR），
   但豁免**计数入账**（job log + step summary 明示"N 项命中经 ADR-XXXX 豁免"）。
   P3-2（#96）ADR scope 实质校验落地前采用引用式校验，落地后自动升级（不阻塞）。
4. **中心维护、钉 hash 复用**：检测器与 fixture 全部在 CI-Workflows 仓维护，业务仓
   caller workflow 以 `uses: Cloudbird-Software/CI-Workflows/.github/workflows/
   test-integrity.yml@<sha>` 接入本仓 gate 的 needs 链（hygiene/check 同款模式）。
   aggregator 严格断言遵循 ADR-0032；本门对非 PR 事件为 n/a-success（推送面无
   base...head 语义），调用方无需登记 EXPECTED_SKIP。
5. **规则/阈值单一声明**在 .github governance/policy/testing.yaml#test_integrity，
   检测器内置同值默认——policy 拉取失败时红（fail-closed）而非裸奔内置默认。
6. **T8 单元级自检常驻**：scripts/test-integrity-fixtures/ 维护 ≥8 个构造 diff
   fixture（四类篡改 + 正常类）+ runner 断言"计数/删除判定/skip 判定与预标注完全
   一致"，随 CI-Workflows 自身 CI 每次变更运行——计数逻辑回归不依赖人工。

## 后果

- 四类篡改注入 PR（#86 T1-T4）全红；正常测试演进/纯重构（T5/T6）全绿；ADR 逃生门
  （T7）绿且豁免计数入账。
- regex 级检测存在误报面（注释含 assert、语义等价改写等）：误报经逃生门（ADR 引
  用）消化并留痕——宁误报不漏报；AST 级解析为后续增强。
- 每业务仓 CI 新增 1 个 job（<5min，testing.yaml gate 预算内）；fetch-depth: 0 全
  历史克隆是 hygiene 先例，无新增成本形态。
- 本门自身被同 PR 削弱（#81 §3.3 自指问题）的防线不在本卡范围：由 #95（gate 上移
  org required workflows）解决；在此之前 CI-Workflows 变更属 C1（owner review +
  adr-required）兜底。
