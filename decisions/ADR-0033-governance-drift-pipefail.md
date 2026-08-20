# ADR-0033: governance-drift 检测步骤 pipefail 修复（GM-1 漂移报警机制失效）

- status: accepted（2026-08-20）
- 背景: P1-1（ADR-0029）T1 漂移注入测试期间的活体发现；ADR-0032 同类缺陷批次
- 关联: .github/workflows/governance-drift.yml、GM-1（GOVERNANCE.yaml）、
  run 32331351942（实证）

## 背景

governance-drift.yml 的检测步骤为：

```
bash governance/drift-check.sh | tee drift-report.txt
```

GitHub Actions 对多行 run 的默认 shell 是 `bash -e`（无 pipefail）——管道退出码
取最后一个命令（tee，恒 0）。drift-check.sh 的 `exit 1` 被吞掉，步骤恒 success：

- 「发现漂移则开 issue」步骤的 `if: failure()` 从不满足 → GM-1 声明的
  "漂移自动开 issue" 机制整体失效；
- 「漂移消除则关闭 issue」步骤（`if: success()`）反而常开——报绿不报红。

实证（2026-08-20 run 32331351942）：drift-check 输出 4 项 DRIFT（含 P1-1
注入的 Use-up-Plan auto-merge-off），步骤结论 success，issue 未开。

## 决策

1. 检测步骤首行加 `set -o pipefail`：drift-check 的真实退出码传导到步骤结论，
   漂移=红=开 issue（GM-1 恢复）；token 缺失（exit 2）与漂移（exit 1）的分
   通道报告逻辑（ADR-0021）不变。
2. 与 ADR-0032（skipped ≠ success）同批落地：检测链路的 fail-open 面一次焊死
   ——aggregator 假绿与检测器假绿是同一类缺陷的两个面。

## 后果

- P1-1 T1 注入测试得以闭环：漂移检出 → run 红 → issue 开；修复 → 全绿 →
  issue 自动关闭（该关闭路径一直正常，只是从未被真正触发过）。
- 类似 `cmd | tee` 形态的步骤（若未来出现）默认要求 pipefail；zizmor 不覆盖
  此类 shell 语义缺陷，依赖评审与实测。