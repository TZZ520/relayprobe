# relayprobe

Languages: English | [简体中文](README.zh-CN.md)

relayprobe is an evidence-oriented audit tool for OpenAI-compatible API relays and LLM gateways.

It is designed to detect observable signs of:

- model mapping or downgrade
- parameter override
- hidden instruction or prompt injection
- stream protocol emulation
- semantic cache reuse
- guardrail redaction or response rewriting
- inconsistent usage or billing fields

The tool does not claim to cryptographically prove that a relay is a direct transparent forwarder. A black-box client cannot prove that without upstream logs, provider request IDs, billing records, or provider-signed attestations. relayprobe reports evidence levels instead.

## Current status

This repository contains a local MVP:

- standard-library Python CLI
- core synthetic probe suite
- mock transport for safe local verification
- live OpenAI-compatible transport for opt-in API checks
- JSON and Markdown reports
- unit tests
- GitHub Actions workflow

## Quick start

Run the local mock suite without any API key:

    $env:PYTHONPATH="src"
    python -m relayprobe doctor
    python -m relayprobe run --mock clean --out artifacts/mock-clean
    python -m relayprobe run --mock tampered --out artifacts/mock-tampered

Run the unit tests:

    $env:PYTHONPATH="src"
    python -m unittest discover -s tests

Detect local API configuration used by Codex, Claude Code, or common CCswitch-style setups without printing raw keys:

    $env:PYTHONPATH="src"
    python -m relayprobe detect-local --out artifacts/local-detect

The local detector scans environment variables and common config files under your user profile. It reports actual base URLs and model names, but API keys/tokens are only shown as redacted values plus a short local fingerprint. Reports are written under `artifacts/`, which is ignored by git.

The summary also classifies the likely active route for Codex and Claude Code: `official_account_login_likely`, `official_api_key`, `official_api_key_default_endpoint_likely`, `official_cloud_api`, `third_party_api`, `local_switcher_or_proxy`, or `unknown`. If a detected base URL points to localhost/loopback, relayprobe probes that local URL without sending any API key and reports `local_switcher_status`.

To run one validation pass against the first detected OpenAI-compatible environment target:

    $env:PYTHONPATH="src"
    python -m relayprobe detect-local --run-first --out artifacts/local-detect

`--run-first` sends only relayprobe's synthetic test prompts to that configured API. It does not upload the local detection report, and it intentionally does not use secrets parsed from config files for network calls.

If you want discovery without even localhost probing, add `--no-probe-local`.

Run against a real relay only when you explicitly provide a synthetic test target:

    $env:PYTHONPATH="src"
    $env:RELAYPROBE_API_KEY="sk-..."
    python -m relayprobe run --base-url "https://your-relay.example.com" --model "gpt-4o" --api-key-env RELAYPROBE_API_KEY --out artifacts/live-relay

Do not use real secrets, private prompts, customer data, or production-only keys in early testing.

## Evidence levels

relayprobe uses conservative result states:

- pass: expected observable behavior was present
- suspect: behavior suggests relay modification, downgrade, caching, filtering, or inconsistency
- fail: protocol or request failed in a way that invalidates the case
- inconclusive: the signal is too weak to classify
- info: useful evidence that does not prove a problem

## Why this approach

Many public LLM gateway projects intentionally support model routing, fallback, caching, guardrails, header override, request transformation, and usage accounting. Those features are legitimate when disclosed, but they are also the exact mechanism by which a third-party relay can stop being a transparent forwarder.

relayprobe therefore tests gateway behavior directly instead of asking the model to self-identify.

## Acknowledgements and prior work

relayprobe was shaped by public work from the LLM gateway, relay, observability, and security-proxy ecosystem. This project is independent and is not affiliated with those projects, but it intentionally credits them because their open work makes this kind of audit tooling easier to reason about.

See [docs/credits.md](docs/credits.md) for the bilingual acknowledgements and reference list, including projects such as [@BerriAI/litellm](https://github.com/BerriAI/litellm), [@Portkey-AI/gateway](https://github.com/Portkey-AI/gateway), [@QuantumNous/new-api](https://github.com/QuantumNous/new-api), [@Calcium-Ion/new-api](https://github.com/Calcium-Ion/new-api), [@songquanpeng/one-api](https://github.com/songquanpeng/one-api), [@Forlives/relay-api-hub](https://github.com/Forlives/relay-api-hub), [@musistudio/claude-code-router](https://github.com/musistudio/claude-code-router), [@farion1231/cc-switch](https://github.com/farion1231/cc-switch), and others.

## Repository layout

    src/relayprobe/      CLI, transports, probes, analyzers, runner
    tests/               standard-library unit tests
    docs/                research notes, threat model, test plan
    cases/               human-readable suite configuration
    .github/workflows/  CI

See [docs/local-detection.md](docs/local-detection.md) for the local-only detection policy and supported config sources.

## Limitations

- Model identity requires a direct official baseline for strong evidence.
- Response integrity cannot be proven end-to-end unless the upstream provider signs responses or exposes independently verifiable request IDs.
- Some guardrail findings indicate legitimate security middleware, not necessarily malicious tampering.
- Live model behavior is probabilistic; repeated runs and direct baselines matter.
