# ADR-0013: 红队演练修复批次——验证器元验证、防线注册表硬化与 ADR 编号唯一性

- status: accepted
- date: 2026-08-18
- deciders: owner + AI
- resolves: 红队演练 issue #9（agent-registry）P0-2 / P1-6 及 PR#8 遗留的 qodo 评审项；关联 .github issue #17/#18、CI-Workflows issue #4（跨仓部分在各自 PR 落地）
- cross-repo: Cloudbird-Software/.github（gate/漂移检测/治理范围批次）、Cloudbird-Software/CI-Workflows（timeout 批次）

## 背景

红队演练对本仓提出（issue #9，均经独立复核确认或反驳）：

1. **P0-2 属实**：validate.py 是注册层唯一验证器（AR-1/AR-2 执行点），但自身正确性无人验证、
   无独立测试套件——若 validate.py 有 bug（如错误放行），治理体系沦为空壳且难以发现。
2. **P1-6 属实**：main 上存在两个 ADR-0011（runtime-egress / team-collaboration）。ADR-0012 已
   记录消歧约定（不重编号、引用带主题限定），但无机器检查防止编号冲突再次发生。
3. **P0-1 部分属实**：governance-core 在 GOVERNANCE.yaml/team.schema/curator 身份中被引用为
   persistent 治理团队，但 registry/teams/ 无此声明。复核结论：ADR-0004 规划的 governance-core
   在 v1.0 已落地为 **team:stewardship**（persistent、成员 curator-main、dev-wave/incident-cell
   的 archive_to 目标）——问题是**陈旧引用**而非缺失团队。新增 governance-core 会造成职责重复
   的第二个 persistent 团队；正确修复是把残留引用更正为 stewardship。
4. **P1-3 / P1-4 / P2(models-gateway) 复核为不属实**：validate.py 已实现跨文件引用校验
   （tools/skills/agents 存在性+status、⑦ 常规引用段）、族级独立性全局比对（全局比对段 +
   team 级比对段）、models.yaml ↔ llm-gateway/config.yaml 别名对齐（gateway 配置对齐段）。
   在 issue 中逐条回复证据行号。

## 决策

1. **validate.py 元验证测试套件（tests/，pytest）**：
   - 正向：未修改的仓库树必须全绿（防回归）。
   - 负向：逐项注入缺陷——ADR 编号冲突、team 无 members、引用未批准 tool、
     族级独立性破坏、ephemeral 缺 archive_to、畸形/未注册 check:* 引用、
     checks.yaml 畸形条目——每项必须被 validate.py 拒绝（exit=1 且命中对应错误信息）。
   - CI 接线：validate.yml 在 PR（head 自洽侧）与 main 各跑一次 pytest。
   - tests/ 纳入 CODEOWNERS owner-only（验证器与其测试同属治理之治理路径）。

2. **checks.yaml 注册表硬化（修复 PR#8 qodo 评审三项）**：
   - 条目结构校验：id 合语法且唯一、status∈{active,planned}、where 非空、
     consumed_externally 布尔——畸形条目 fail 而非静默授权。
   - 引用侧完整 token 匹配：捕获 [A-Za-z0-9_-]+ 全串再校验语法
     （防 `check:gate_typo` 被前缀截断读作已注册的 gate）；标识前加词边界（防
     `healthcheck:x` 误匹配）。
   - 诊断路径相对各自扫描根（standards→标准侧、registry→数据侧），
     base-validator/head-data 双 checkout 场景报错路径正确。

3. **adr-required check 实装并转 active（CT-CUR-003 闭环）**：
   - 本仓 validate.yml：PR 触及 C1 路径（standards/|scripts/|decisions/|.github/|CODEOWNERS|tests/）
     时，PR body/title 必须含 `ADR-\d{4}`（词边界匹配，防子串伪造），且被引 ADR 文件须存在于
     PR head 的 decisions/；PR 文件清单分页读取（--paginate，防 >100 文件漏检）。
   - .github gate.yml：同规则（C1 路径为该仓布局）；PR 文件清单 --paginate、
     正则词边界（防 NOTADR-0013junk 子串绕过）。被引 ADR 的**存在性**校验不在
     PR 上下文做——agent-registry 为私有仓，PR 上下文 GITHUB_TOKEN 无跨仓读权，
     注入 org secret 则向 PR 控制的代码暴露凭据（zizmor secret-exposure 模型）；
     存在性由 .github drift-check.sh §10 后验（每日、可信 main 上下文、独立 7 天
     窗口）：窗口内合并 PR 的 ADR 引用须真实存在于 agent-registry/decisions/。
   - checks.yaml 中 adr-required 由 planned → active；ADR-0012 的实装待办清零。

4. **ADR 编号唯一性机器检查**：
   - validate.py 扫描 decisions/ADR-NNNN-slug.md：编号冲突即 FAIL。
   - 唯一豁免：ADR-0011 历史双档（ADR-0012 决定不重编号，代码内显式记录豁免及出处）。

5. **团队成员下限**：所有 team 声明 members ≥ 1（schema v2 已定 minItems:1，validate 补执行
   侧）——persistent 团队无成员 = 无人对治理资产负责（issue #9 P0-1 建议的 machine 侧落地）。

6. **governance-core 陈旧引用更正为 stewardship**：本仓 curator-main.md 身份文件；.github 仓
   GOVERNANCE.yaml（AR-6/flows）与 team.schema 示例在配套 PR 中更正。ADR-0004/0007 为历史
   决策记录不改写（其中 governance-core 是当时规划名，落地形态即 stewardship）。

## 后果

- validate.py 的正确性有了可复跑的回归基线；后续修改验证器必须同时通过负向测试树。
- 悬空防线（未注册 check）、畸形防线引用（typo/大小写/下划线）从"静默放行"变为 CI 拒绝。
- C1 变更"无 ADR 不合并"从约定变为机器检查（adr-required active；owner-only review 仍在）。
- ADR 编号冲突不可能再次合入（0011 历史冲突按 ADR-0012 约定豁免）。
- 代价：新增 ADR/团队/check 声明的门槛各多一步（登记/成员/编号唯一性）——与"声明即执行"一致。
