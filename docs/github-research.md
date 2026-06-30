# GitHub research notes

Chinese readers can also see [README.zh-CN.md](../README.zh-CN.md), [docs/github-research.zh-CN.md](github-research.zh-CN.md), and [docs/credits.md](credits.md).

This document summarizes public GitHub findings that shaped the relayprobe MVP. The purpose is to understand real-world capabilities and test surfaces, not to imply that any referenced project is malicious.

## Existing detection projects

- [@Forlives/relay-api-hub](https://github.com/Forlives/relay-api-hub): focuses on detecting whether Claude/GPT/Gemini relay APIs are watered down. It checks stream fingerprints, usage fields, reasoning/math, code quality, and response consistency. Useful reference, but several checks are heuristic and some rely on self-reported model identity or small samples.

## Gateway and relay projects with relevant capabilities

- [@BerriAI/litellm](https://github.com/BerriAI/litellm): OpenAI-compatible AI gateway for many providers, with virtual keys, spend tracking, guardrails, load balancing, and admin features.
- [@Portkey-AI/gateway](https://github.com/Portkey-AI/gateway): AI gateway with retries, fallbacks, load balancing, conditional routing, and guardrails.
- [@QuantumNous/new-api](https://github.com/QuantumNous/new-api) / [@Calcium-Ion/new-api](https://github.com/Calcium-Ion/new-api): AI API gateway and management systems. Code inspection confirmed model mapping, parameter override, header override, system prompt override, cache/usage accounting, and request field removal logic.
- [@songquanpeng/one-api](https://github.com/songquanpeng/one-api): One API base project. Code inspection confirmed model mapping and relay metadata support.
- [@MartialBE/one-hub](https://github.com/MartialBE/one-hub) and [@aiprodcoder/MIXAPI](https://github.com/aiprodcoder/MIXAPI): One API/New API derivatives for multi-channel model distribution and billing.
- [@maximhq/bifrost](https://github.com/maximhq/bifrost): AI gateway with automatic fallbacks, load balancing, semantic caching, and governance.
- [@Helicone/helicone](https://github.com/Helicone/helicone): observability and gateway platform with routing, fallback, prompt management, and logging.
- [@katanemo/plano](https://github.com/katanemo/plano): agentic proxy/data plane with routing, orchestration, filter chains, moderation, and smart routing.

## Local coding-client routers and switchers

- [@musistudio/claude-code-router](https://github.com/musistudio/claude-code-router): a Claude Code routing project. Its ecosystem influenced relayprobe's local config detection paths for Claude Code router-style setups.
- [@farion1231/cc-switch](https://github.com/farion1231/cc-switch): a cross-platform desktop assistant/switcher for Claude Code, Codex, OpenCode, OpenClaw, Gemini CLI, and related tools.
- [@huangdijia/ccswitch](https://github.com/huangdijia/ccswitch): a CLI profile switcher for Claude Code API configurations.

## Security proxy and guardrail projects

- [@ax128/AegisGate](https://github.com/ax128/AegisGate): security gateway with request/response-side policies, PII/secret redaction, prompt injection detection, response sanitization, and audit logging.
- [@techlab-innov/llmtrace](https://github.com/techlab-innov/llmtrace): transparent LLM proxy with real-time security checks, PII scanning, cost control, streaming metrics, and observability.

## Main implementation implications

The public ecosystem already contains legitimate middleware features that can alter a request or response:

1. model aliasing and mapping
2. conditional routing and fallback
3. parameter override
4. header override
5. hidden system/instruction injection
6. disabled-field removal
7. prompt injection and PII filters
8. semantic caching
9. stream protocol translation
10. usage and cost normalization
11. local profile/config switching

relayprobe treats these as test targets. A finding means observable behavior consistent with modification; it does not automatically prove malicious intent.
