# relayprobe

Languages: English | [简体中文](README.zh-CN.md)

relayprobe is an evidence-oriented audit tool for OpenAI-compatible API relays and LLM gateways.

Important: the one-command quickstart uses the machine owner's detected real OpenAI-compatible API key/base URL/model for one local synthetic probe run when available. This may create API usage and cost. Raw keys are not printed, written to reports, or uploaded.

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
- live OpenAI-compatible transport for detected local API checks
- JSON and Markdown reports
- unit tests
- GitHub Actions workflow

## Quick start: how to run it after cloning

relayprobe does not require a server deployment. It is a local Python CLI tool.

### 1. Clone and install

PowerShell / Windows:

    git clone https://github.com/TZZ520/relayprobe.git
    cd relayprobe
    python -m pip install -e .

If you do not want to install it, run with `PYTHONPATH=src`:

    $env:PYTHONPATH="src"
    python -m relayprobe doctor

### One-command quickstart

If you just want to run the full local workflow and see the output format, run the root script:

Windows PowerShell:

    powershell -ExecutionPolicy Bypass -File .\quickstart.ps1

Windows batch / double-click:

    .\quickstart.bat

macOS / Linux:

    bash ./quickstart.sh

If you have already run `python -m pip install -e .`, you can also run:

    relayprobe quickstart --out artifacts/quickstart

The one-command quickstart now tries to use the machine owner's currently detected real OpenAI-compatible API key/base URL/model for one live synthetic probe run after the project self-test, clean mock, tampered mock, and local Codex / Claude Code / CCswitch route detection.

This may create API usage and cost. The key is used only in the local process for the Authorization header; relayprobe does not print raw keys, write raw keys to reports, or upload them. Generated reports stay under the local `artifacts/` directory, which is ignored by git.

To skip the real-key live probe and run only local checks:

PowerShell:

    powershell -ExecutionPolicy Bypass -File .\quickstart.ps1 -NoRunDetectedLive

Installed CLI:

    relayprobe quickstart --no-run-detected-live --out artifacts/quickstart-offline

### 2. Run the project self-test first

Recommended first command:

    relayprobe self-test --out artifacts/self-test

It prints all 15 test items with a human-readable status such as `PASS / 通过`. This confirms the local checkout is working.

### 3. Run local mocks to understand normal and tampered output

No API key is needed:

    relayprobe run --mock clean --out artifacts/mock-clean
    relayprobe run --mock tampered --out artifacts/mock-tampered

`clean` simulates a normal relay.
`tampered` simulates a modified relay and should produce multiple `SUSPECT / 可疑` findings.

### 4. Detect where local Codex / Claude Code / CCswitch is pointing

    relayprobe detect-local --out artifacts/local-detect

This scans environment variables and common config files and reports:

- whether Codex looks like it uses official API, third-party API, or a local proxy
- whether Claude Code looks like it uses official API, third-party API, or local CCswitch/proxy
- whether a loopback API is reachable
- actual base URL and model name
- redacted API key/token presence, never raw secrets

Disable even localhost probing with:

    relayprobe detect-local --no-probe-local --out artifacts/local-detect

### 5. Run against a real relay

Only use synthetic test targets. Do not use private prompts, customer data, production-only keys, or sensitive content:

    $env:RELAYPROBE_API_KEY="sk-..."
    relayprobe run --base-url "https://your-relay.example.com" --model "gpt-4o" --api-key-env RELAYPROBE_API_KEY --out artifacts/live-relay

### 6. Read the statuses

relayprobe prints each test item with a plain status:

- `PASS / 通过`: expected behavior was observed
- `SUSPECT / 可疑`: behavior suggests modification, downgrade, caching, filtering, or field inconsistency
- `FAIL / 失败`: request or protocol failed
- `INCONCLUSIVE / 证据不足`: the signal is too weak to classify
- `INFO / 信息`: useful metadata, not proof by itself

Reports are written under `artifacts/` by default. The directory is ignored by git.

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
