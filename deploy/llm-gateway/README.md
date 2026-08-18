# LLM Gateway 部署指南（ADR-0002 rev1）

回答"要不要起服务器"：**要一台常驻机器**，但极轻（1C/512M 即可）——家里的盒子/NAS/VPS 都行；起步阶段用你日常开发机常驻也可。所有 agent（无论在哪台机器、哪个 swarm 实例）都只连它。

## 三步部署

```bash
cd deploy/llm-gateway
cp .env.example .env && vim .env        # ① 填 provider key + master key
sed -i 's/<UPSTREAM_MODEL_A>/你的真实模型名/' config.yaml   # ② 把 4 个 TODO 占位换成真实 provider/模型
docker compose up -d                    # ③ 起服务（常驻）
curl -s http://localhost:4000/health/liveliness   # 验证
```

## 发 per-team key（用量计量/配额的单位）

```bash
curl -X POST http://localhost:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"models": ["coder-fast","reviewer"], "max_budget": 50, "tpm": 200000, "team_id": "dev-wave"}'
```
返回的 `key` 即该团队专属 `LLM_GATEWAY_KEY`（配额尽自动限流；failover 在组内自动发生，团队无感）。

## agent 侧接线（一次性，之后全自动）

运行 agent swarm 的机器只设两个 env（secret manager / 部署脚本注入，不落仓库）：

```
LLM_GATEWAY_ENDPOINT=http://<gateway机器>:4000
LLM_GATEWAY_KEY=sk-<该团队的 virtual key>
```

之后任何 swarm 启动即自动接入；换模型/加节点/调配额只改本目录 config.yaml（走 PR），全部 agent 立即生效，声明零改动。

## 上游运行时（openjiuwen）

不 fork、不用 submodule（ADR-0002 rev1）：上游官方镜像 `openJiuwen-ai/jiuwenswarm`，
部署渲染器执行时 `git clone --depth 1 -b <pinned-tag>` 锁定版本；pin 关系随渲染器配置版本化。
A2X 注册中心（分布式 Team 控制面）同源上游 `openJiuwen-ai/agent-protocol`。
