# ADR-0044: gh-app-token.sh 加固——Windows 兼容、jq 降级可选、安装令牌缓存

- status: accepted（2026-08-20）
- 背景: .github issue #101（Shorts_Director 规划工作中首次使用即踩中问题 1/2，
  2026-08-20 故障记录）
- 关联: .github 仓 `scripts/gh-app-token.sh`、`scripts/ghcb`（新增）、AG-1（agent
  认证入口）、ADR-0029/0031（auto-merge 链路消费本脚本产物）

## 背景

gh-app-token.sh 是 agent 与 GitHub 交互的唯一推荐认证入口，但在 Windows
（Git Bash/MSYS2）下不可用，且每次调用都完整走 JWT 签名 + 两次 API 往返：

1. 签名用进程替换 `openssl dgst -sha256 -sign <(printf ...)`——Windows 版
   openssl 读不了 MSYS2 的 `/proc/<pid>/fd/N`，报
   `Could not open file or uri for loading private key`。
2. jq 硬依赖——Windows 默认无 jq，四处浅层 JSON 操作全部中断。
3. 无令牌缓存——安装令牌 1h 有效，交互式会话内多次调用重复签名+请求。

## 决策

1. **签名改临时文件**：`mktemp` 落盘私钥（600）+ `trap` 清理，签名后即刻删除；
   Linux/macOS 行为不变，纯兼容性修复。
2. **JSON 工具降级链**：`jq → python3/python → node` 依序探测，任一可用即可；
   全部缺失时明确报错并列安装建议。四处操作（installation 查询 / 构造
   request body / 解析 token / 解析 expires_at）的 fallback 保持单键/取字段
   级简单度，不引入新格式依赖。Windows 下 jq 输出可能带 CRLF，所有 jq
   输出统一 `tr -d '\r'` 防令牌尾部带回车。
3. **安装令牌缓存**：`~/.cache/cloudbird/gh-app-token-<org>-<repo>.json`
   （权限 600；XDG_CACHE_HOME 可重定向），内容 `{token, expires_at}`。调用时
   距过期 >5 分钟直接输出缓存令牌（零网络）；否则走完整换令牌并回写。
   `--refresh` 强制刷新（排障用）。缓存损坏（非 JSON）→ 警告并自动刷新，
   不静默失败。安全注记：缓存含短期凭据，文件权限必须 600、路径不得落在
   仓库或共享目录（脚本头部注释声明）。
4. **便捷入口 `scripts/ghcb`**：`GH_TOKEN=$(ghcb <repo>)` 一行完成取令牌；
   stdout=令牌（可命令替换），人类提示走 stderr。
5. 依赖声明同步（脚本头注释）：openssl 必需；bash+curl+openssl+一个 JSON
   工具（jq/python/node 任一）。CI 用法（AGENT_APP_SECRET env 注入私钥）不变。

## 后果

- Windows Git Bash 开箱可用（本 ADR 配套 PR 在 Windows Git Bash 实测冷缓存/
  二次命中/--refresh 三条路径 + 三类负例）；Linux/macOS 无回归。
- 一小时内重复调用零网络请求（缓存命中路径无任何 curl）。
- 令牌落盘引入新的短期凭据持有面：1h 过期 + 600 权限 + 用户主目录限定，
  与"磁盘不落长期凭据"原则一致（私钥仍不落新位置）。
