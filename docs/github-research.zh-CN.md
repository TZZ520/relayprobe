# GitHub 调研记录

本文记录 relayprobe 设计阶段参考过的公开 GitHub 项目。完整致谢见 [docs/credits.md](credits.md)。

## 已有检测项目

- [@Forlives/relay-api-hub](https://github.com/Forlives/relay-api-hub)
  - 这是一个直接检测 Claude/GPT/Gemini 中转是否“掺水”的项目。
  - 它使用了 SSE 指纹、usage 字段、推理/数学能力、代码质量和响应一致性等思路。
  - relayprobe 参考了它的问题意识，但采用更保守的证据分级，不依赖单次模型自称。

## 网关与中转项目

- [@BerriAI/litellm](https://github.com/BerriAI/litellm)
  - 统一 OpenAI 兼容接口、多 provider 调用、虚拟 Key、成本追踪、guardrails、负载均衡。

- [@Portkey-AI/gateway](https://github.com/Portkey-AI/gateway)
  - retries、fallback、load balancing、conditional routing、guardrails。

- [@QuantumNous/new-api](https://github.com/QuantumNous/new-api) / [@Calcium-Ion/new-api](https://github.com/Calcium-Ion/new-api)
  - 中文生态常见 API 管理与分发系统。
  - 公开代码中可见 model_mapping、param_override、header_override、system_prompt_override、cache/usage accounting 等能力。
  - 这些能力本身不等于恶意，但正是审计工具需要检测的透明度边界。

- [@songquanpeng/one-api](https://github.com/songquanpeng/one-api)
  - 中文生态影响很大的统一 API 管理和分发项目，很多后续中转项目都受其启发。

- [@MartialBE/one-hub](https://github.com/MartialBE/one-hub)
  - One API 派生项目，扩展了更多模型和统计能力。

- [@aiprodcoder/MIXAPI](https://github.com/aiprodcoder/MIXAPI)
  - 聚合 New API、One API 和多种三方能力的大模型 API 网关项目。

- [@maximhq/bifrost](https://github.com/maximhq/bifrost)
  - 多 provider 统一接口、fallback、负载均衡、语义缓存和治理能力。

- [@Helicone/helicone](https://github.com/Helicone/helicone)
  - LLM observability、gateway、prompt management、fallback 和成本/延迟分析。

- [@katanemo/plano](https://github.com/katanemo/plano)
  - agentic proxy、模型路由、编排、filter chain、moderation 和智能路由。

## 安全代理与 Guardrail 项目

- [@ax128/AegisGate](https://github.com/ax128/AegisGate)
  - 请求侧和响应侧安全代理、PII/secret 脱敏、prompt injection 检测、危险响应处理和审计日志。

- [@techlab-innov/llmtrace](https://github.com/techlab-innov/llmtrace)
  - 透明代理、实时安全检测、PII 扫描、成本控制、流式指标和观测能力。

## 对 relayprobe 的影响

这些项目帮助我们明确中转 API 可能具备的真实能力：

1. 模型映射
2. 条件路由
3. fallback 降级
4. 参数覆盖
5. Header 覆盖
6. 系统提示词或 instruction 注入
7. 请求字段删除
8. prompt injection 检测和 PII 脱敏
9. 语义缓存
10. 流式协议转换
11. usage 与计费归一化

relayprobe 不评价这些能力的动机。它只关心：当一个服务声称自己是透明直连时，这些行为是否可观察、可复现、可被记录。

