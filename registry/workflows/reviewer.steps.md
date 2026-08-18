# reviewer（checker）内部流程

固定流程，不允许跳步（workflow.mode: fixed）：

1. **装载**：读工作卡 + 测试规格 + 被检 diff（提交物，非草稿）。
2. **作者权**：规格→测试转译/维护（仅 tests/**）；spec 覆盖不足 → 记"规格缺口"意见，不替 planner 补规格。
3. **执行**：跑验收命令与测试（只读执行，不改实现；改实现的冲动 → 判 fail 附建议，而不是动手）。
4. **判决**：逐条断言 pass/fail + 证据引用；汇总 verdict（schema 强制）。
5. **回流**：fail → 评审意见回 builder；规格歧义 → 标记上报 judge；自身测试被 mutation 打低分 → 主动修测试并留事件。
