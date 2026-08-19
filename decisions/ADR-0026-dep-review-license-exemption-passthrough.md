# ADR-0026: dep-review 增加 allow-dependencies-licenses 可选透传输入（许可证归一化误报精确豁免）

- status: accepted（2026-08-19）
- 关联: ADR-0023（AI_Web_School 治理接入）、ADR-0011（team-collaboration v1 / scorecard 姿态）

## 背景

AI_Web_School T-W0-010（19 个 security 警报清除）要求 CI 以 `--require-hashes`
安装 Python 依赖（Scorecard Pinned-Dependencies）。pip 在该模式下要求 extras
闭包内的每个分发包都有独立 requirement 行——`psycopg[binary]` 因此必须拆出
`psycopg-binary==3.3.4` 独立行。拆行后 GitHub 依赖图把 psycopg-binary 的许可证
判定为 GPL-3.0-or-later（PyPI 元数据实为 LGPL-3.0-only；LGPL 前缀归一化伪影），
`dependency-review-action@v5` 按 org deny 清单（AGPL-3.0/GPL-3.0/SSPL-1.0）误报阻断。

实测两条不可行路径（留痕）：

1. 把 psycopg-binary 的哈希挂在 `psycopg[binary]` 行上——pip 不认，extras 闭包
   分发包必须有独立行；
2. 本仓 `.github/dependency-review-config.yml` 默认路径——v5.0.0 仅在显式传
   `config-file` 输入时读取配置文件（源码 config.ts readConfig），默认路径不会被
   自动加载。

## 决策

1. CI-Workflows `dep-review.yml` 增加 workflow_call 可选输入
   `allow-dependencies-licenses`（PURL 逗号分隔列表，默认空串），原样透传给
   dependency-review-action 同名输入。
2. 空串安全性已核对源码：action 侧 `getOptionalInput` 对空串返回 undefined
   （v5.0.0 config.ts:98-101），不传该输入的调用仓行为逐字节不变。
3. org deny 清单本体（AGPL-3.0/GPL-3.0/SSPL-1.0）不变；豁免按包名精确化，
   由调用仓在自己的 ci.yml 中自证并留痕（首个使用者：AI_Web_School 对
   `pkg:pypi/psycopg-binary` 的豁免，依据 PyPI 元数据 LGPL-3.0-only）。
4. 豁免不得用于清单内生态的真实 GPL/AGPL/SSPL 包；drift-check 若发现以本输入
   豁免 deny 清单本意（真实 GPL 包放行）视为治理违规。

## 后果

- 调用仓获得误报豁免的显式通道，不再需要 fork 复用工作流或在调用仓内联复制
  action（两者都破坏 CI-1 集中维护基线）。
- 每次豁免都在调用仓 ci.yml 可审计，dependency-review 摘要评论同时留痕。
