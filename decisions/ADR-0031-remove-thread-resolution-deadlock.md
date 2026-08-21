# ADR-0031: 拆除 required_review_thread_resolution 死锁 + 机器反馈通道规范（P1-2）（墓碑）

- status: accepted
- lifecycle: active
- archive: https://github.com/Cloudbird-Software/archive/blob/main/adr/ADR-0031-remove-thread-resolution-deadlock.md
- migrated: W1-C1（ADR-0053），正文已迁 archive 仓；本文件保留编号可解析性（adr-required 按文件名校验）。

required_review_thread_resolution 拆除（无人团队的永久 pending 死锁）+ bot-channels 规范：机器意见只走 check run annotation/普通评论，禁止创建 review thread 与自我授权。
