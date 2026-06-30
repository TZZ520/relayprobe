# GitHub research notes

This document summarizes public GitHub findings that shaped the relayprobe MVP.

## Existing detection projects

- Forlives/relay-api-hub: focuses on detecting whether Claude/GPT/Gemini relay APIs are watered down. It checks stream fingerprints, usage fields, reasoning/math, code quality, and response consistency. Useful reference, but several checks are heuristic and some rely on self-reported model identity or small samples.

## Gateway and relay projects with relevant capabilities

- BerriAI/litellm: OpenAI-compatible AI gateway for many providers, with virtual keys, spend tracking, guardrails, load balancing, and admin features.
- Portkey-AI/gateway: AI gateway with retries, fallbacks, load balancing, conditional routing, and guardrails.
- QuantumNous/new-api / Calcium-Ion/new-api: AI API gateway and management system. Code inspection confirmed model_mapping, param_override, header_override, system_prompt_override, cache/usage accounting, and request field removal logic.
- songquanpeng/one-api: One API base project. Code inspection confirmed model mapping and relay metadata support.
- MartialBE/one-hub and aiprodcoder/MIXAPI: One API/New API derivatives for multi-channel model distribution and billing.
- maximhq/bifrost: AI gateway with automatic fallbacks, load balancing, semantic caching, and governance.
- Helicone/helicone: observability and gateway platform with routing, fallback, prompt management, and logging.
- ax128/AegisGate and techlab-innov/llmtrace: security proxies with prompt injection detection, PII redaction, response filtering, and audit logging.
- katanemo/plano: agentic proxy/data plane with routing, orchestration, filter chains, moderation, and smart routing.

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

relayprobe treats these as test targets. A finding means observable behavior consistent with modification; it does not automatically prove malicious intent.

