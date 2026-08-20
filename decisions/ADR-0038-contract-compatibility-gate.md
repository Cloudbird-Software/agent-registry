# ADR-0038: 契约兼容性检测门——OpenAPI breaking + JSON Schema breaking + DB migration 前后兼容（P2-4）

- status: accepted（2026-08-20）
- 背景: .github issue #81（自动合并计划）§4.1 工作卡 #89（P2-4）
- 关联: CI-Workflows `contract.yml`/`scripts/contract/`、`.github` 仓 `governance/policy/contracts.yaml`、
  AI_Web_School `contract.yml`（contract-watch，P5 冻结检测——职责互补非替代）、
  ADR-0032（gate aggregator 严格化）、ADR-0023（AI_Web_School 治理接入）、
  policy/testing.yaml G-01（contract_api_drift，trigger: first_public_api）

## 背景

组织的 risk_posture 第一条是 customer_upgrade_failure——客户本地部署，升级/回滚炸 =
收入损失。API 契约破坏（删 endpoint、字段改型）和 destructive migration（DROP
COLUMN、改列型、无默认值加 NOT NULL 列）是最典型的升级炸弹：它们在 diff 里看起来
人畜无害，无人 review 下只能靠机器发现（#81 §4.1）。

盘点结论（2026-08-20，工作卡 #89 执行步骤 1）：

| 仓 | 契约面 | 形态 |
|---|---|---|
| AI_Web_School | `specs/contracts/**` + `alembic/versions/**` | JSON Schema + alembic 迁移 |
| Shorts_Director | `schema/contracts/**`、`schema/entities/**` | JSON Schema |
| agent-registry | `registry/schemas/**` | JSON Schema（L1 声明层） |
| template-service | 无 | ——（N/A 显式路径的模板载体） |
| agent-platform | 仅 `vendor/agent-registry/` 拷贝 | 非源头（source of truth 在 agent-registry） |
| mutual | `spec/01-schemas.md` | 散文 schema，不可机判 |
| 其余仓 | 无 | —— |

**全组织当前无 OpenAPI、无 proto 文件**。

## 决策

1. **新增可复用 workflow `CI-Workflows/.github/workflows/contract.yml`**（job
   `contract-check`），业务仓以 `uses:` 挂入自身 `ci.yml` 并加入 gate `needs` 链（对齐
   ADR-0032 aggregator 范式：显式 needs、严格断言、不设事件条件——PR 与 push 两个事件面
   都真跑，无 EXPECTED_SKIP 登记需求）。不采纳工作卡 #89"check.yml 内新增 job"的字面
   方案：check.yml 是 `make check` 运行时载体，契约检测与其无运行时耦合；独立 reusable
   workflow 使业务仓 needs 链显式可见（P1-3 建立的接入范式），且避免 check.yml 钉扎
   bump 时隐式改变全部消费仓行为。
2. **引擎** `CI-Workflows/scripts/contract/contract_check.py`（纯 Python 标准库 +
   pyyaml），三种检测面按 policy 声明的 kind 分派：
   - `openapi` → `oasdiff breaking --fail-on WARN`（版本 1.29.1 + tarball sha256 双锚定，
     对齐 gitleaks 锚定范式）。退出码语义：0=兼容、1=breaking、其他=工具错误（一律红，
     fail-closed）。`--fail-on WARN` 而非 ERR：oasdiff 把"删除可选响应属性"归为
     warning——对客户本地部署同样是升级炸弹，从严。
   - `jsonschema` → 内置结构化 breaking 分类器（组织真实契约形态；oasdiff 不覆盖纯
     JSON Schema）。breaking 判定：type 改变、required 收紧（新增必填）、属性删除、
     enum 收窄、`additionalProperties: false` 新增。新增可选属性/放宽约束=兼容。本地
     `$ref`（`#/definitions/*`、`#/$defs/*`）跟随解析。
   - `proto` → **policy 不接受该 kind**（声明即报错）。组织无 proto；待首个 proto 仓
     落地时实装 `buf breaking`（版本锚定）并修订本 ADR。fail-closed 而非静默跳过。
3. **DB migration 检测**（policy 声明迁移目录后激活）：按语句分类 DDL——
   destructive 清单：`DROP TABLE/INDEX/VIEW/CONSTRAINT`、`DROP COLUMN`、`ALTER COLUMN
   TYPE/SET DATA TYPE`、`SET NOT NULL`、加列 `NOT NULL` 无 `DEFAULT`、`RENAME
   TABLE/COLUMN`、`TRUNCATE`、`DROP DEFAULT`、MySQL `MODIFY/CHANGE COLUMN`、无
   `NOT VALID` 的 `ADD CONSTRAINT`；additive：建表、加可空列、带 DEFAULT 加列、建
   索引、`NOT VALID` 加约束、enum 加值。alembic（`op.*` 调用 + `op.execute` 内嵌
   SQL）与裸 SQL 双前端，同一分类核心。destructive 判定须给出文件:行号。
4. **destructive 的完备手续**（卡内 T4 语义）：destructive 迁移满足以下两条才绿——
   (a) PR title/body 引用 `ADR-NNNN` 且被引 ADR 存在于 agent-registry/decisions/
   （公开仓，GITHUB_TOKEN 可读，防幽灵 ADR；push 事件无 title/body 可引用 →
   destructive 直推 main 一律红——破玻璃场景接受短暂红，恢复路径=补 ADR 记录）；
   (b) 回滚脚本存在且含逆操作：alembic → 同文件 `downgrade()` 须含对应逆操作类
   （drop_column↔add_column/create_table、drop_table↔create_table、ALTER TYPE↔
   alter_column、SET NOT NULL↔nullable=True 放宽等，逆映射显式落盘引擎）。
   OpenAPI/JSON Schema breaking 同理要求 ADR 引用（policy 严格度：
   `breaking_requires_adr: true`），无"回滚脚本"概念故只查 ADR。
5. **检测器失明防护**（卡内 T6，验收最后一条）：policy 声明的每个契约 glob 在 HEAD
   必须命中 ≥1 文件、声明的迁移目录必须存在且非空——找不到即红。同时 `git diff` 中
   声明路径下的 D（删除/移走）条目直接红（若为移动须同步更新 policy 声明并引用 ADR）。
   防止"把契约文件移走让检测器失明"。
6. **policy 落盘** `.github` 仓 `governance/policy/contracts.yaml`：各仓契约路径
   （kind+glob）、迁移目录与工具、destructive DDL 模式清单、ADR/豁免要求。引擎优先
   读 org policy（gh api 公开仓读）；**404 时回退引擎内置 bootstrap 快照**
   （CI-Workflows `scripts/contract/policy-bundled.yaml`，大声 WARN 标注来源）——组织
   policy 合入前业务仓 PR 的 contract job 可独立变绿；policy 拉取的其他错误（网络/API）
   一律红（fail-closed）。为封堵"改内置快照绕过 org policy"：CI-Workflows ci.yml 的
   adr-required C1 路径正则扩充纳入 `scripts/`。
7. **N/A 显式化**（卡内步骤 4）：未声明契约面的仓，contract-check 真跑并输出明确
   `N/A: <repo> 未声明契约/迁移面（policy: <来源>）` 日志后成功退出——不是 skipped
   （ADR-0032：skipped≠success），不依赖路径过滤。
8. **自测**：CI-Workflows 自身 ci.yml 新增 `contract-selftest` job，跑
   `contract_check.py --selftest`——内嵌 fixture 全套：T1（OpenAPI 删 endpoint/改型→
   红）、T2（加可选字段/加 endpoint→绿）、T3/T4/T5（alembic destructive 无 ADR→红、
   ADR+downgrade 逆操作→绿、additive→绿）、T6（policy 声明路径失配→红）、T7（≥12
   条预标注 DDL fixture 分类逐条断言）。接 selftest 入本仓 gate needs。
9. **本次接线范围**：template-service（N/A 模板载体）、AI_Web_School（alembic 迁移 +
   specs/contracts）、Shorts_Director（JSON Schema）。agent-registry 契约在 policy 中
   声明但接线**延后**：其 `validate.yml` 是单 job 架构（gate job 内联全部检查，无
   needs 聚合层），接入需先做 aggregator 拆分重构——独立小卡处理，本卡在 #89 留言
   记录。agent-platform（vendor 拷贝非源头）、mutual（散文 schema）不声明不接线。
10. **业务仓钉扎**：contract.yml 引用钉 CI-Workflows 引擎分支 commit SHA
    （bootstrap 钉扎）；引擎 PR squash 合入并走 v1.X.Y 发布四步流程后，业务仓改钉
    merge SHA（各 PR body 注明合并顺序与改钉步骤）。不得引用可变 `@main`。

## 后果

- 声明了契约的仓：breaking 契约变更红（除非引用真实存在的 ADR）、destructive
  migration 无 ADR 或缺回滚脚本红、additive/兼容变更绿；契约文件被移走/声明失配红。
- 未声明契约的仓：job 显式 N/A 成功，不误报、不静默 skip。
- `--fail-on WARN` 比社区默认（ERR）严：删除可选响应属性即红。误报出口=ADR 引用
  （留痕），不提供注释式豁免标记（防 agent 自我豁免——与 #87 抑制标记预算门同一
  威胁模型）。
- proto 检测未实装：组织无 proto 文件，policy 声明 proto 即报错（fail-closed），
  首个 proto 仓落地时须先修订本 ADR 实装 buf breaking。
- bootstrap 期存在内置 policy 快照与 org policy 双源：快照仅是过渡态，org policy
  合入后引擎始终优先 org policy，快照漂移不影响判定；后续清理卡可移除快照回退。
- push 面（直推 main）发现 destructive migration 一律红：破玻璃直推含 destructive
  DDL 时 main CI 短暂红属预期信号，恢复路径=补 ADR 记录（ADR-0030 同型）。
