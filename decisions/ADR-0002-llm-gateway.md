# ADR-0002: 模型接入 = LLM Gateway 常驻服务，alias 是唯一接口

- status: accepted
- date: 2026-08-18

## 修订记录

### rev1 (2026-08-18)
- Gateway 部署配置落盘位置由"openjiuwen 私有仓 deploy/llm-gateway"改为 **本仓 `deploy/llm-gateway/`**：与 models.yaml 同仓，validate.py 强制 gateway config 的 model_name 集合与 models.yaml alias 集合一致（防声明与网关漂移）。
- openjiuwen **不 fork 私有仓**：上游官方镜像 `openJiuwen-ai/jiuwenswarm`（A2X 注册中心 = `openJiuwen-ai/agent-protocol`），REPOS.yaml `external_upstreams` 段声明，部署渲染时 clone + pin tag。
- 不使用 submodule 引用上游：agent-registry 的消费者（validate/渲染）不需要框架源码随仓分发；submodule 指针随上游高频提交过期，且 recursive clone 膨胀。需要源码的场景按需 clone 固定 tag。

## 背景

模型选型在实现中不是一个名字，而是三件事：接 API、用量监控、多节点路由（单节点用量耗尽自动切换）。且 provider key 不能进仓库，也不能要求每次搭 agent swarm 时人工粘贴。

## 决策

1. 部署常驻 **LLM Gateway**（候选 LiteLLM proxy；部署配置版本化于 openjiuwen 私有仓 `deploy/llm-gateway`）。
2. `models.yaml` 只声明 **alias → route_group + 配额档 + 约束**；节点、provider、key 的解析只存在于 gateway。
3. **key 一次性注入** gateway 的 secret store（部署环境 env / secret manager）；agent 侧统一持有 gateway key（per-team/per-agent 维度），实现用量计量与配额。任何仓库/声明/agent 本地配置零明文 key。
4. agent swarm 启动时凭 `LLM_GATEWAY_ENDPOINT + LLM_GATEWAY_KEY`（env 注入）自动接入，无人工粘贴。

## 后果

- 换模型/加节点/调配额 = 改 gateway 配置，全部 agent 立即生效，声明不变。
- 用量数据从 gateway 侧采集，进入事件流（run_finished）。
- 风险：gateway 成为单点，需高可用部署；短期接受单实例。
