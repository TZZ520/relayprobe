# relayprobe 测试方案

## 目标

检测 API 中转、聚合网关或三方代理是否表现得不像一个透明的 OpenAI 兼容直连转发器。

这个项目强调“证据”，不是靠一次模型回答下结论。每个测试都应该保存请求摘要、响应内容、状态码、SSE 事件、usage 字段和分析结果，方便复现。

## 三种模式

### 黑盒模式

只有中转 API，没有官方对照。这个模式可以发现异常，但不能证明真实上游 provider 或真实模型。

适合检测：

- 参数是否明显失效
- 流式协议是否异常
- 是否复用缓存
- usage 是否自洽
- 是否有明显脱敏、过滤、前后缀注入

### 差分模式

同时有中转 API 和官方 provider API。这个模式可以做更强的模型身份、参数生效和行为分布对比。

适合检测：

- 模型是否疑似降级
- 同参数下输出分布是否明显不同
- context window 是否异常变小
- 错误格式、usage 字段、stream 事件是否和官方差异过大

### 取证模式

有官方账单、上游请求 ID、服务端日志或 provider 签名。只有这个模式才接近“证明是否真实直连”。

## 核心测试套件

| 套件 | 目的 |
|---|---|
| request integrity | 用 nonce echo 和 exact-output 检测可见请求/响应改写。 |
| parameter override | 检测 max_tokens、stop、JSON mode 等参数是否被忽略或覆盖。 |
| model identity | 检测返回 model 字段是否不一致，并为后续行为指纹预留接口。 |
| hidden prompt | 检测 exact-output 任务里是否出现意外前缀、政策文本或拒答内容。 |
| stream protocol | 捕获 SSE 行，判断是否像真实流式协议。 |
| cache detection | 使用唯一 nonce 检测近似问题是否复用旧响应。 |
| guardrail redaction | 使用合成 fake secret 检测脱敏、过滤或响应改写。 |
| usage consistency | 检查 prompt_tokens、completion_tokens、total_tokens 是否自洽。 |

## 每次运行必须保存的证据

- run metadata
- 不含 API Key 的 target metadata
- canonical request body hash
- 合成请求体
- 响应状态码
- 可解析 JSON 响应
- 原始响应体
- SSE event lines
- 耗时
- findings 和 severity

## 结果等级

- pass：观察到符合预期的行为
- suspect：观察到疑似改写、降级、缓存、过滤或计费异常
- fail：请求或协议失败，导致该用例无效
- inconclusive：证据不足
- info：有参考价值，但不能证明问题

## 安全约束

- 只使用合成提示词。
- 不提交 .env、API Key、真实业务提示词、客户数据或生产报告。
- 不把模型自称当成强证据。
- 没有官方 baseline 时，不断言真实模型身份。
- 没有上游签名或可验证 request id 时，不断言响应端到端未被改写。

## 面向国内开发者的说明

很多国内 API 中转服务会基于 One API、New API 或其派生项目做渠道聚合、计费、限速、模型映射和分发。这些能力本身不是坏事，企业内部也经常需要。但如果服务商宣传“原样转发”或“指定模型直连”，却没有披露模型映射、参数覆盖、fallback 或缓存行为，就需要被测试。

relayprobe 的定位是帮助开发者形成可复现证据，而不是制造无根据指控。

