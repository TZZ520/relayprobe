# Acknowledgements and references / 致谢与参考项目

relayprobe is an independent project. It is not affiliated with, endorsed by, or derived from the projects below. We reference them because their public code and documentation show real-world LLM gateway, relay, security, observability, local-switching, and detection patterns.

relayprobe 是一个独立项目，并不是下面这些项目的分支，也不代表这些项目为 relayprobe 背书。我们列出它们，是因为这些公开项目展示了真实世界中 LLM 网关、中转、路由、安全代理、观测、本地配置切换和检测工具的工程实践。公开透明的项目值得被尊重。

## Detection and audit inspiration / 检测与审计方向

- [@Forlives/relay-api-hub](https://github.com/Forlives/relay-api-hub)
  - English: A relay-audit project focused on detecting watered-down Claude/GPT/Gemini relay APIs. It inspired parts of the problem framing, while relayprobe uses its own evidence model and implementation.
  - 中文：这是一个直接面向“AI API 中转是否掺水”的检测项目，提供了 SSE 指纹、usage 字段、推理能力、代码质量、一致性等检测思路。relayprobe 没有复制其实现，但认可它对中文开发者场景的启发价值。

## Gateway and relay systems / 网关与中转系统

- [@BerriAI/litellm](https://github.com/BerriAI/litellm)
  - English: A major AI gateway/proxy project showing multi-provider routing, virtual keys, cost tracking, guardrails, and load balancing.
  - 中文：展示了统一 OpenAI 兼容接口、多 provider 调用、虚拟 Key、成本追踪、guardrails、负载均衡等生产级网关能力。

- [@Portkey-AI/gateway](https://github.com/Portkey-AI/gateway)
  - English: A gateway project with retries, fallbacks, load balancing, conditional routing, and guardrail patterns.
  - 中文：展示了 retries、fallback、load balancing、conditional routing、guardrails 等典型 AI Gateway 能力。

- [@QuantumNous/new-api](https://github.com/QuantumNous/new-api) and [@Calcium-Ion/new-api](https://github.com/Calcium-Ion/new-api)
  - English: New API style projects show common API management and distribution features, including model mapping, parameter override, header override, system prompt override, and cache/usage accounting.
  - 中文：New API 系项目展示了中文生态常见的 API 管理与分发系统能力。公开代码中可看到 model mapping、parameter override、header override、system prompt override、cache/usage accounting 等设计。这些能力本身不等于恶意，但正是审计工具需要检测的透明度边界。

- [@songquanpeng/one-api](https://github.com/songquanpeng/one-api)
  - English: A widely influential unified API management and distribution project in the Chinese LLM ecosystem.
  - 中文：One API 是中文生态中影响很大的统一 API 管理和分发项目，很多后续项目都受其启发或基于其二次开发。

- [@MartialBE/one-hub](https://github.com/MartialBE/one-hub)
  - English: A One API derivative with expanded model support, statistics, and function-calling improvements.
  - 中文：One API 派生项目，补充了更多模型、统计和函数调用相关能力。

- [@aiprodcoder/MIXAPI](https://github.com/aiprodcoder/MIXAPI)
  - English: A Chinese LLM API gateway combining New API, One API, and additional third-party gateway capabilities.
  - 中文：聚合 New API、One API 和多种三方能力的中文大模型 API 网关项目。

- [@maximhq/bifrost](https://github.com/maximhq/bifrost)
  - English: A multi-provider gateway with fallback, load balancing, semantic caching, and governance features.
  - 中文：展示了多 provider 统一接口、fallback、负载均衡、语义缓存和治理能力。

- [@Helicone/helicone](https://github.com/Helicone/helicone)
  - English: An LLM observability and gateway project with prompt management, fallback, logging, and cost/latency analytics.
  - 中文：展示了 LLM observability、gateway、prompt management、fallback、日志以及成本/延迟分析等能力。

- [@katanemo/plano](https://github.com/katanemo/plano)
  - English: An agentic proxy/data-plane project with routing, orchestration, filter chains, moderation, and smart routing patterns.
  - 中文：展示了 agentic proxy、模型路由、编排、filter chain、moderation 和智能路由思路。

## Local coding-client routers and switchers / 本地编程客户端路由与切换器

- [@musistudio/claude-code-router](https://github.com/musistudio/claude-code-router)
  - English: A Claude Code routing project that makes local model-provider routing and config conventions visible to developers. relayprobe references this ecosystem when designing local config discovery paths.
  - 中文：这是一个 Claude Code 路由项目，让本地模型 provider 路由和配置约定更容易被开发者理解。relayprobe 在设计本地配置发现路径时参考了这类生态实践。

- [@farion1231/cc-switch](https://github.com/farion1231/cc-switch)
  - English: A cross-platform assistant/switcher for Claude Code, Codex, OpenCode, OpenClaw, Gemini CLI, and related coding clients.
  - 中文：这是一个面向 Claude Code、Codex、OpenCode、OpenClaw、Gemini CLI 等工具的跨平台切换/助手项目。relayprobe 对 CCswitch 类配置的本地检测是为了帮助用户确认这些工具当前实际指向的 API。

- [@huangdijia/ccswitch](https://github.com/huangdijia/ccswitch)
  - English: A command-line profile switcher for Claude Code API configurations.
  - 中文：这是一个用于管理和切换 Claude Code API 配置的命令行工具。relayprobe 尊重这类工具对中文开发者工作流的实际价值。

## Security proxy and guardrail systems / 安全代理与 Guardrail 系统

- [@ax128/AegisGate](https://github.com/ax128/AegisGate)
  - English: A security gateway showing request/response-side policies, PII/secret redaction, prompt injection detection, response sanitization, and audit logging.
  - 中文：展示了请求侧和响应侧安全代理、PII/secret 脱敏、prompt injection 检测、危险响应处理和审计日志能力。

- [@techlab-innov/llmtrace](https://github.com/techlab-innov/llmtrace)
  - English: A transparent LLM proxy with real-time security checks, PII scanning, cost control, streaming metrics, and observability.
  - 中文：展示了透明代理、实时安全检测、PII 扫描、成本控制、流式指标和观测能力。

## How relayprobe uses these references / relayprobe 如何使用这些参考

relayprobe uses these projects as prior art for threat modeling and test design. It does not copy their code. The public capabilities exposed by these projects help define what an audit tool should test:

relayprobe 将这些项目作为威胁建模和测试设计的先验参考，并不复制它们的代码。它们公开展示的能力帮助我们确定审计工具需要检测什么：

1. model mapping / 模型映射
2. conditional routing / 条件路由
3. fallback / fallback 降级
4. parameter override / 参数覆盖
5. header override / Header 覆盖
6. system prompt or instruction injection / 系统提示词或 instruction 注入
7. semantic cache / 语义缓存
8. guardrail redaction / guardrail 脱敏
9. stream protocol conversion / 流式协议转换
10. usage and billing normalization / usage 与计费归一化
11. local config/profile switching / 本地配置与 profile 切换

If we missed a project or mischaracterized a capability, please open an issue or PR. The intent is to credit prior work accurately and respectfully.

如果有遗漏项目，或者对某个项目能力的描述不准确，欢迎开 issue 或 PR。这个文件的目标是准确、尊重地标注前人的工作。
