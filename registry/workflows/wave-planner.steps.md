# wave-planner（planner）内部流程

固定流程（workflow.mode: fixed）：

1. **意图解析**：intent → 目标/约束/不变量；引用 policy/*.yaml 而非自创规则。
2. **现状调研**：经 researcher-code 查代码库/文档/判例；现状不明 → 计划暂停，先补调研卡。
3. **波次分解**：依赖+风险排序；单波次可独立验证回滚。
4. **工作卡**：每卡=目标/边界/验收引用（[ci] 优先）/依赖卡号；无验收引用的卡不允许存在。
5. **测试规格**：每卡配"验证什么"规格（不含实现描述）。
6. **自检提交**：wave-plan schema 校验 + 卡完整性 → 验收示例送 owner 批准（intent.ratified_by）→ 开工；结构问题被 validate 驳回则逐条响应后重提。
