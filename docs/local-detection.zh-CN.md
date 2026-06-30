# 本地 API 配置检测

`relayprobe detect-local` 用来检查本机 AI 编程工具当前能看到的 API 配置，重点覆盖 Codex、Claude Code，以及 CCswitch / Claude Code Router 这类本地切换器或中转配置。

它的定位是“本地自查”，主要回答这些问题：

- 当前工具实际指向哪个 base URL？
- 当前配置的目标模型名是什么？
- 本机是否存在 API Key 或 auth token？
- 当前环境变量里有没有可以直接跑一轮 OpenAI-compatible 验证的目标？

## 命令

只做发现，不联网跑探针：

    $env:PYTHONPATH="src"
    python -m relayprobe detect-local --out artifacts/local-detect

发现配置后，对第一个可运行的 OpenAI-compatible 环境变量目标跑一轮合成探针：

    $env:PYTHONPATH="src"
    python -m relayprobe detect-local --run-first --out artifacts/local-detect

`--run-first` 只会使用环境变量里检测到的 OpenAI-compatible 目标。它不会拿配置文件里解析出的密钥去自动联网。

## 一键跑通的真实 Key 行为

默认情况下，`detect-local` 只发现本机配置，不会拿配置文件里的 Key 自动请求真实 API。

一键跑通 `quickstart` 不同：它会尝试使用机主当前本机检测到的真实 OpenAI-compatible API Key/base URL/model 跑一次真实合成探针。这会产生真实 API 调用记录，并可能产生费用。Key 只在本机当前进程内用于 Authorization；relayprobe 不会明文打印 Key，不会把原始 Key 写进报告，也不会上传。

如果想让一键跑通只跑本地自检、mock 和配置发现，不使用真实 Key：

    relayprobe quickstart --no-run-detected-live --out artifacts/quickstart-offline

PowerShell：

    powershell -ExecutionPolicy Bypass -File .\quickstart.ps1 -NoRunDetectedLive

如果是 `detect-local`，真实测试仍然需要显式加参数：

    relayprobe detect-local --run-detected-live --out artifacts/local-detect-live

关闭 localhost 探测，只做配置发现：

    $env:PYTHONPATH="src"
    python -m relayprobe detect-local --no-probe-local --out artifacts/local-detect

## 输出里的路由判断

JSON 报告里会包含 `summary.codex_route_type`、`summary.claude_code_route_type` 和 `summary.local_switcher_status`。更详细的证据在 `assessment` 字段里。

路由类型：

- `official_account_login_likely`：发现 Codex/Claude 的官方账号登录或凭据文件，并且没有自定义三方 base URL 优先覆盖。
- `official_api_key`：检测到官方 provider 端点和 key/token。
- `official_api_key_default_endpoint_likely`：检测到 key/token，但没有自定义 base URL，因此大概率走官方默认端点。
- `official_cloud_api`：检测到 Azure OpenAI 等官方云端点。
- `third_party_api`：检测到非官方、非本地的 base URL。
- `local_switcher_or_proxy`：检测到 base URL 指向 `localhost`、`127.0.0.1`、`::1` 或其他 loopback 地址。
- `unknown`：证据不足，暂时无法判断。

本地切换器状态：

- `reachable`：检测到 loopback base URL，并且本地 HTTP 探测有响应。
- `configured_but_unreachable`：配置里有 loopback base URL，但本地探测没有响应。
- `configured_not_probed`：配置里有 loopback base URL，但你通过 `--no-probe-local` 关闭了探测。
- `config_detected_no_local_url`：发现了 CCswitch/router 类配置文件，但没有检测到 loopback base URL。
- `not_detected`：没有发现本地切换器或本地代理证据。

## 隐私和安全策略

- relayprobe 不会上传本地检测报告。
- 报告默认写到 `artifacts/`，该目录已被 `.gitignore` 忽略。
- API Key 和 auth token 不会以原文写进 JSON 报告。
- Key 只显示类似 `sk-a...5678` 的脱敏形式，并提供一个 8 位 SHA-256 指纹，方便你在本机比对“是不是同一把 key”。
- base URL 和模型名会显示，因为这正是要检测的核心信息。
- 如果有人把凭证塞进 URL，例如 `https://user:pass@example.com` 或 `?api_key=...`，relayprobe 会把这些部分脱敏。
- 本地切换器探测只访问 loopback/localhost URL，并且不发送 API Key。
- `--run-first` 会把 relayprobe 的合成测试提示词发到当前配置的 API 端点；如果你完全不想产生网络请求，不要加这个参数。

## 当前扫描哪些来源

环境变量目标：

- OpenAI / Codex 风格：`OPENAI_API_KEY`、`CODEX_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_API_BASE`、`CODEX_BASE_URL`、`CODEX_API_BASE`、`OPENAI_MODEL`、`OPENAI_DEFAULT_MODEL`、`CODEX_MODEL`
- Claude Code / Anthropic 风格：`ANTHROPIC_API_KEY`、`ANTHROPIC_AUTH_TOKEN`、`CLAUDE_API_KEY`、`CLAUDE_AUTH_TOKEN`、`ANTHROPIC_BASE_URL`、`ANTHROPIC_API_URL`、`CLAUDE_BASE_URL`、`CLAUDE_API_BASE`、`CLAUDE_CODE_BASE_URL`、`ANTHROPIC_MODEL`、`ANTHROPIC_SMALL_FAST_MODEL`、`CLAUDE_MODEL`、`CLAUDE_CODE_MODEL`
- Azure OpenAI 风格：`AZURE_OPENAI_API_KEY`、`AZURE_OPENAI_ENDPOINT`、`AZURE_OPENAI_DEPLOYMENT`、`AZURE_OPENAI_MODEL`
- 显式 CCswitch 风格：`CCSWITCH_API_KEY`、`CCSWITCH_AUTH_TOKEN`、`CCSWITCH_BASE_URL`、`CCSWITCH_API_BASE`、`CCSWITCH_ENDPOINT`、`CCSWITCH_MODEL`、`CCSWITCH_DEFAULT_MODEL`

用户目录下常见配置文件：

- `.codex/config.toml`、`.codex/config.json`、`.codex/auth.json`
- `.claude.json`、`.claude/config.json`、`.claude/settings.json`、`.claude/settings.local.json`、`.claude/.credentials.json`
- `.config/claude-code/config.json`
- `.config/ccswitch/config.json`、`.ccswitch/config.json`
- `.claude-code-router/config.json`
- `%APPDATA%/Claude/claude_desktop_config.json`
- `%APPDATA%/Codex/config.json`
- `%APPDATA%/ccswitch/config.json`

如果设置了 `CODEX_HOME`、`CODEX_CONFIG_DIR`、`CLAUDE_CONFIG_DIR`、`CLAUDE_CODE_CONFIG_DIR`、`CCSWITCH_HOME` 或 `CCSWITCH_CONFIG_DIR`，relayprobe 也会继续扫描这些目录下的常见配置文件。

## 当前限制

- 联网探针目前只支持 OpenAI-compatible 协议。
- Claude Code / Anthropic 配置会被发现和脱敏展示，但还不会自动跑 Anthropic Messages 协议探针。
- 配置文件解析是保守的 best-effort：JSON 会结构化解析；TOML 类文件目前使用简单 key/value 提取。
- 黑盒客户端能收集强证据，但如果没有上游日志、request id、账单记录或服务商签名，无法密码学证明“绝对原样直连”。
