# Local API configuration detection

`relayprobe detect-local` helps you inspect the API settings currently visible to local AI coding tools such as Codex, Claude Code, and CCswitch-style switchers.

The command is intentionally local-only. It is meant to answer practical questions such as:

- Which base URL is my tool currently pointed at?
- Which model name is configured?
- Is an API key or auth token present?
- Would relayprobe be able to run one OpenAI-compatible validation pass from the current environment?

## Commands

Discovery only:

    $env:PYTHONPATH="src"
    python -m relayprobe detect-local --out artifacts/local-detect

Discovery plus one synthetic OpenAI-compatible probe run:

    $env:PYTHONPATH="src"
    python -m relayprobe detect-local --run-first --out artifacts/local-detect

`--run-first` only uses a runnable OpenAI-compatible target from environment variables. It does not use secrets parsed from config files for network calls.

## Explicit live API test mode

By default, `detect-local` and `quickstart` discover local configuration but do not automatically use keys parsed from config files to call a real API.

If the machine owner explicitly authorizes one live synthetic probe run using the currently detected OpenAI-compatible API key/base URL/model, use:

    relayprobe detect-local --run-detected-live --out artifacts/local-detect-live

or:

    relayprobe quickstart --run-detected-live --out artifacts/quickstart-live

The PowerShell script also supports:

    powershell -ExecutionPolicy Bypass -File .\quickstart.ps1 -RunDetectedLive

When enabled, relayprobe reads a detected local key and sends synthetic test requests. This may create API usage and cost. The key is used only in process memory for Authorization; it is not printed, written to reports, or uploaded.

Disable even localhost probing:

    $env:PYTHONPATH="src"
    python -m relayprobe detect-local --no-probe-local --out artifacts/local-detect

## Route classification in the output

The JSON report contains `summary.codex_route_type`, `summary.claude_code_route_type`, and `summary.local_switcher_status`. The detailed evidence lives under `assessment`.

Route types:

- `official_account_login_likely`: a known Codex/Claude auth or credential file was found, with no custom third-party base URL taking precedence.
- `official_api_key`: an official provider endpoint plus key/token was detected.
- `official_api_key_default_endpoint_likely`: a key/token was detected without a custom base URL, so the tool likely falls back to the official default endpoint.
- `official_cloud_api`: an official cloud endpoint such as Azure OpenAI was detected.
- `third_party_api`: a non-official, non-local base URL was detected.
- `local_switcher_or_proxy`: the detected base URL points to `localhost`, `127.0.0.1`, `::1`, or another loopback address.
- `unknown`: relayprobe did not find enough evidence to classify the route.

Local switcher status:

- `reachable`: a detected loopback base URL responded to a local HTTP probe.
- `configured_but_unreachable`: a loopback base URL was configured, but no local probe endpoint responded.
- `configured_not_probed`: a loopback base URL was configured, but probing was disabled with `--no-probe-local`.
- `config_detected_no_local_url`: a CCswitch/router-like config file was found, but no loopback base URL was detected.
- `not_detected`: no local switcher/router evidence was found.

## Privacy and safety policy

- No report is uploaded by relayprobe.
- Reports are written under `artifacts/` by default, and `artifacts/` is ignored by git.
- API keys and auth tokens are never stored in report JSON as raw values.
- Keys are shown as a short redaction such as `sk-a...5678` plus an 8-character SHA-256 fingerprint for local comparison.
- Base URLs and model names are shown because they are the point of the check.
- Credentials embedded inside URLs, such as `https://user:pass@example.com` or `?api_key=...`, are redacted.
- Local switcher probing only touches loopback/localhost URLs and sends no API key.
- `--run-first` sends relayprobe's synthetic test prompts to the configured API endpoint. Do not use it if you do not want any network request.

## Sources scanned

Environment-variable targets:

- OpenAI/Codex style: `OPENAI_API_KEY`, `CODEX_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_API_BASE`, `CODEX_BASE_URL`, `CODEX_API_BASE`, `OPENAI_MODEL`, `OPENAI_DEFAULT_MODEL`, `CODEX_MODEL`
- Claude Code/Anthropic style: `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_API_KEY`, `CLAUDE_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_URL`, `CLAUDE_BASE_URL`, `CLAUDE_API_BASE`, `CLAUDE_CODE_BASE_URL`, `ANTHROPIC_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`, `CLAUDE_MODEL`, `CLAUDE_CODE_MODEL`
- Azure OpenAI style: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_MODEL`
- Explicit CCswitch-style names: `CCSWITCH_API_KEY`, `CCSWITCH_AUTH_TOKEN`, `CCSWITCH_BASE_URL`, `CCSWITCH_API_BASE`, `CCSWITCH_ENDPOINT`, `CCSWITCH_MODEL`, `CCSWITCH_DEFAULT_MODEL`

Common config files under the user profile:

- `.codex/config.toml`, `.codex/config.json`, `.codex/auth.json`
- `.claude.json`, `.claude/config.json`, `.claude/settings.json`, `.claude/settings.local.json`, `.claude/.credentials.json`
- `.config/claude-code/config.json`
- `.config/ccswitch/config.json`, `.ccswitch/config.json`
- `.claude-code-router/config.json`
- `%APPDATA%/Claude/claude_desktop_config.json`
- `%APPDATA%/Codex/config.json`
- `%APPDATA%/ccswitch/config.json`

If `CODEX_HOME`, `CODEX_CONFIG_DIR`, `CLAUDE_CONFIG_DIR`, `CLAUDE_CODE_CONFIG_DIR`, `CCSWITCH_HOME`, or `CCSWITCH_CONFIG_DIR` is set, relayprobe also checks the expected config files under those directories.

## Current limitations

- Live probing is currently OpenAI-compatible only.
- Claude Code/Anthropic settings are detected and redacted, but not yet used for a live Anthropic Messages probe.
- Config-file parsing is deliberately conservative and best-effort; JSON is parsed structurally, while TOML-like files use simple key/value extraction.
- A local black-box client can collect strong evidence, but it cannot cryptographically prove transparent forwarding without upstream logs, request IDs, billing records, or provider-signed attestations.
