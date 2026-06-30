# relayprobe project status / 项目状态

Last coordinated project refresh / 最近一次统一整理时间：

- Time: 2026-06-30 12:05:13 +08:00
- Repository: https://github.com/TZZ520/relayprobe
- Verified base commit before this status stamp: `da27ebc Improve human-readable CLI output`

## What was verified / 已验证内容

- `python -m unittest discover -s tests`
  - Result: 13 tests passed.
  - 结果：13 个单测全部通过。
- `python -m relayprobe self-test`
  - Result: every test item is shown with a human-readable status such as `PASS / 通过`.
  - 结果：每个测试项都会明文展示测试内容和状态。
- `python -m relayprobe run --mock clean`
  - Result: clean mock reports normal behavior.
  - 结果：干净 mock 中转表现正常。
- `python -m relayprobe run --mock tampered`
  - Result: tampered mock reports multiple `SUSPECT / 可疑` findings.
  - 结果：被篡改 mock 能触发多项可疑结果。
- `python -m relayprobe detect-local`
  - Result: local route detection prints Codex / Claude Code route type, local switcher status, and final active route summary.
  - 结果：本地检测会输出 Codex / Claude Code 路由类型、本地代理状态和最终实际中转路径。

## Safety note / 安全说明

relayprobe does not upload local configuration reports. API keys and auth tokens are redacted in reports and CLI output. Local switcher probing only touches loopback/localhost URLs and sends no API key.

relayprobe 不上传本地配置报告。API Key 和 auth token 会在报告和命令行输出中脱敏。本地代理探测只访问 loopback/localhost 地址，并且不会发送 API Key。

