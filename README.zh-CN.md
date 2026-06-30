# relayprobe 中文说明

语言： [English](README.md) | 简体中文

relayprobe 是一个面向 OpenAI 兼容 API 中转、聚合网关、三方代理服务的证据型审计工具。

它的目标不是简单问模型“你是谁”，而是从请求、响应、参数、流式协议、缓存、计费和行为指纹等角度收集证据，判断一个中转 API 是否存在可观察的改写、降级、过滤或伪装迹象。

## 它要检测什么

relayprobe 当前 MVP 重点覆盖：

- 模型映射或模型降级
- temperature、max_tokens、stop、response_format 等参数是否被覆盖或忽略
- 是否存在隐藏 system prompt 或 instructions 注入
- 流式响应是否是真正的 SSE 协议链路
- 是否存在语义缓存或旧响应复用
- 是否存在 PII、密钥、敏感词等 guardrail 脱敏或响应改写
- usage 字段和 token 计费字段是否自洽
- 返回的 model 字段是否和请求一致

## 重要边界

黑盒测试无法密码学证明“这个中转一定是原始直连”。如果没有上游服务商的请求日志、账单记录、可验证 request id 或响应签名，客户端只能得到证据强弱，而不能得到绝对证明。

因此 relayprobe 的输出不会写成“百分百真实”或“百分百造假”，而是使用保守等级：

- pass：观察到符合预期的行为
- suspect：观察到疑似改写、降级、缓存、过滤或计费异常
- fail：请求或协议失败，导致该用例无效
- inconclusive：证据不足
- info：有参考价值，但不能证明问题

## 快速开始

不需要 API Key，先跑本地 mock：

    $env:PYTHONPATH="src"
    python -m relayprobe doctor
    python -m relayprobe run --mock clean --out artifacts/mock-clean
    python -m relayprobe run --mock tampered --out artifacts/mock-tampered

运行测试：

    $env:PYTHONPATH="src"
    python -m unittest discover -s tests

针对真实中转 API 运行时，请只使用合成测试目标，不要放真实业务提示词、客户数据、生产密钥或隐私内容：

    $env:PYTHONPATH="src"
    $env:RELAYPROBE_API_KEY="sk-..."
    python -m relayprobe run --base-url "https://your-relay.example.com" --model "gpt-4o" --api-key-env RELAYPROBE_API_KEY --out artifacts/live-relay

## 为什么这么设计

公开的 LLM Gateway、One API/New API 系统、安全代理和观测平台，已经合法且广泛地支持这些能力：

1. 模型别名和模型映射
2. 条件路由和 fallback
3. 参数覆盖
4. Header 覆盖
5. 系统提示词或 instructions 注入
6. 请求字段删除
7. prompt injection 检测和 PII 脱敏
8. 语义缓存
9. 流式协议转换
10. usage 和成本归一化

这些能力本身不一定恶意。它们在企业网关、安全代理和成本治理里很有价值。但如果一个第三方中转服务没有说明这些行为，却对外宣称“原样转发”或“指定模型直连”，这些能力就会变成需要审计的风险点。

relayprobe 的设计思路就是：不评价动机，只检测可观察行为。

## 项目结构

    src/relayprobe/      CLI、transport、probe、analyzer、runner
    tests/               标准库 unittest 测试
    docs/                调研记录、测试方案、致谢与参考项目
    cases/               人类可读的测试套件说明
    .github/workflows/  GitHub Actions

## 致谢与参考项目

relayprobe 参考了很多公开项目暴露出的网关能力、检测方向和工程事实。它不是这些项目的分支，也不代表这些项目存在恶意行为。相反，正因为这些项目公开、透明，我们才能更准确地理解 LLM 中转和网关系统的真实能力边界。

完整列表见 [docs/credits.md](docs/credits.md)。

特别感谢并尊重这些项目及其维护者：

- [@BerriAI/litellm](https://github.com/BerriAI/litellm)
- [@Portkey-AI/gateway](https://github.com/Portkey-AI/gateway)
- [@QuantumNous/new-api](https://github.com/QuantumNous/new-api)
- [@Calcium-Ion/new-api](https://github.com/Calcium-Ion/new-api)
- [@songquanpeng/one-api](https://github.com/songquanpeng/one-api)
- [@Forlives/relay-api-hub](https://github.com/Forlives/relay-api-hub)
- [@Helicone/helicone](https://github.com/Helicone/helicone)
- [@maximhq/bifrost](https://github.com/maximhq/bifrost)
- [@ax128/AegisGate](https://github.com/ax128/AegisGate)
- [@techlab-innov/llmtrace](https://github.com/techlab-innov/llmtrace)
- [@katanemo/plano](https://github.com/katanemo/plano)

如果后续发现遗漏了重要项目或作者，欢迎补充。尊重前人的工作，是这个项目必须坚持的基本态度。

## 安全提醒

- 不要提交 .env、API Key、真实请求日志或私有提示词。
- 不要把模型自称当成强证据。
- 不要在没有官方 baseline 的情况下断言真实模型身份。
- 不要把 guardrail/脱敏行为直接等同于恶意，它也可能是合法安全策略。

