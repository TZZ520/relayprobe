# relayprobe

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

## Repository layout

    src/relayprobe/      CLI, transports, probes, analyzers, runner
    tests/               standard-library unit tests
    docs/                research notes, threat model, test plan
    cases/               human-readable suite configuration
    .github/workflows/  CI

## Limitations

- Model identity requires a direct official baseline for strong evidence.
- Response integrity cannot be proven end-to-end unless the upstream provider signs responses or exposes independently verifiable request IDs.
- Some guardrail findings indicate legitimate security middleware, not necessarily malicious tampering.
- Live model behavior is probabilistic; repeated runs and direct baselines matter.

