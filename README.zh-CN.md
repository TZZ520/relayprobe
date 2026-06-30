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

## 快速开始：拿到项目后怎么跑

relayprobe 不需要部署服务器。它是一个本地 Python CLI 工具，克隆下来就可以跑。

### 1. 克隆并安装

PowerShell / Windows：

    git clone https://github.com/TZZ520/relayprobe.git
    cd relayprobe
    python -m pip install -e .

如果你不想安装，也可以每次用 `PYTHONPATH=src` 方式运行：

    $env:PYTHONPATH="src"
    python -m relayprobe doctor

### 一键跑通（最推荐新手先用）

如果只是想确认项目能不能跑、输出长什么样，直接执行：

    relayprobe quickstart --out artifacts/quickstart

它会自动完成：项目自检、正常 mock、篡改 mock、本地 Codex / Claude Code / CCswitch 路由检测，并把报告统一写到 `artifacts/quickstart`。

### 2. 先跑项目自检

推荐新手第一步先跑：

    relayprobe self-test --out artifacts/self-test

它会逐条显示 13 个测试项，每条都有测试内容和状态，例如 `PASS / 通过`。这一步用来确认你本地项目本身是正常的。

### 3. 跑本地 mock，先理解正常和异常输出

不需要 API Key，先跑两个本地模拟：

    relayprobe run --mock clean --out artifacts/mock-clean
    relayprobe run --mock tampered --out artifacts/mock-tampered

`clean` 表示正常中转的模拟结果。
`tampered` 表示被篡改/掺水中转的模拟结果，会出现多项 `SUSPECT / 可疑`。

### 4. 检测本机 Codex / Claude Code / CCswitch 当前走哪里

    relayprobe detect-local --out artifacts/local-detect

这个命令会扫描环境变量和用户目录下常见配置文件，告诉你：

- Codex 当前更像走官方 API、三方 API，还是本地代理
- Claude Code 当前更像走官方 API、三方 API，还是本地 CCswitch / proxy
- 本地 loopback API 是否可访问
- 实际 base URL 和模型名
- API Key / token 只脱敏展示，不会明文输出

如果你连 localhost 探测都不想做，可以加：

    relayprobe detect-local --no-probe-local --out artifacts/local-detect

### 5. 真正检测某个中转 API

请只使用合成测试目标，不要放真实业务提示词、客户数据、生产密钥或隐私内容：

    $env:RELAYPROBE_API_KEY="sk-..."
    relayprobe run --base-url "https://your-relay.example.com" --model "gpt-4o" --api-key-env RELAYPROBE_API_KEY --out artifacts/live-relay

### 6. 怎么看结果

relayprobe 会用明文状态展示每个测试项：

- `PASS / 通过`：这个测试项表现正常
- `SUSPECT / 可疑`：观察到疑似篡改、降级、缓存、过滤或字段异常
- `FAIL / 失败`：请求或协议失败
- `INCONCLUSIVE / 证据不足`：信号太弱，不能判断
- `INFO / 信息`：有参考价值，但不能单独证明问题

所有输出报告默认写到 `artifacts/`，该目录已被 `.gitignore` 忽略，不会提交到 GitHub。

本地检测策略和支持的配置来源见 [docs/local-detection.zh-CN.md](docs/local-detection.zh-CN.md)。

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

本地检测策略和支持的配置来源见 [docs/local-detection.zh-CN.md](docs/local-detection.zh-CN.md)。

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
- [@musistudio/claude-code-router](https://github.com/musistudio/claude-code-router)
- [@farion1231/cc-switch](https://github.com/farion1231/cc-switch)
- [@huangdijia/ccswitch](https://github.com/huangdijia/ccswitch)
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
