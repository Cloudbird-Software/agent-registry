# ADR-0047: 意图入口 issue form 与治理标签全集（IR-0001 W0-C2）

- status: accepted（2026-08-21）
- 背景: IR-0001（.github#128，spec v3）W0-C2 工作卡 .github#131
- 关联: spec IFACE-01/IFACE-03（表单≡IR schema v1、状态全集）、DECISION-04
  （状态机以 label 为载体，不建 Projects v2）、GOVERNANCE.yaml GM-1/GM-2
  （期望状态落盘 + C1 变更流程）、ADR-0020（全仓公开）

## 背景

IR-0001 要求"人类只写/签意图"的入口落在 GitHub issue 上：任意仓可用统一
issue form 提交意图，签署后由 conductor（W0-C3）按 `state:*` 标签路由。这
要求两件治理资产存在且可机检：① 表单字段 ≡ IR schema v1（IFACE-01：九字段
全必填）；② 状态标签全集（IFACE-03：十态）+ `type:intent`/`type:card` 作为
期望状态落盘——否则标签靠人手建、漂移不可见，状态机是空中楼阁。

## 决策

1. `.github/ISSUE_TEMPLATE/intent.yml` 落组织默认仓（.github 仓根 .github/
   目录）：九字段一一对应 IR schema v1（job/触发场景/痛点证据/期望的可观察
   变化/非目标/约束/验收证据/可逆性偏好/质量-速度旋钮，全必填），创建即自动
   打 `type:intent`。平台约束：org 默认模板仅对未自带 ISSUE_TEMPLATE 的仓生
   效——产品仓（template-service 派生）自带模板目录时不继承，属已知边界，
   各仓按需引入（W0 不扩面）。
2. 治理标签全集进 `expected-state.json#labels.items`：10 个 `state:*`
   （ir-draft/ir-signed/spec/redteam/wave-planned/ready/in-progress/
   quarantine/needs-human/done）+ `type:intent`/`type:card`。**新增式**：只
   对账存在性与 color/description，不要求排他——各仓既有业务标签（bug/P0/
   gate 等 40+）一律不动、不改名、不删除。
3. apply.sh 新增 §7：期望标签幂等同步到全部受管仓（PATCH 对齐形状，404 即
   POST 创建），沿用 §5 仓库基线的全仓清单与 exclude_repos 豁免；drift-check
   新增 §16：逐仓对账存在性与形状，缺失即漂移（items 为空=fail-closed）。
4. 状态标签的**设置权**不在本 ADR 范围：INV-02（仅 owner 或 cloudbrid-agent
   可置 `state:*`）由 conductor（W0-C3）执法；本 ADR 只落"标签存在且形状正
   确"。bootstrap 期已存在的 6 个标签（state:ir-signed/state:ready/
   state:spec/state:in-progress/type:*）由 §7 收编对齐形状。

## 后果

- 意图入口从"手工 markdown issue"升级为结构化表单，spec-author（W0-C4）可
  按字段定位输入；表单↔schema 的严格机检由 W1-C1 spec.schema.json 与 g010
  吸收（W0 以表单结构本身为保证，字段清单见本 ADR 决策 1）。
- 每受管仓 +12 标签（一次性）；apply.sh 每仓至多 12 次幂等 API 调用；
  drift-check 每仓 1-2 次标签清单 GET。
- 回滚：删除 expected-state#labels 段 + 各仓删除对应标签即整体停用，无数据
  迁移、无 workflow 依赖。
