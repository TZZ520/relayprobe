# relayprobe test plan

## Goal

Detect observable evidence that an API relay is not behaving like a transparent OpenAI-compatible forwarder.

## Modes

### Black-box mode

Only the relay is available. This can detect anomalies but cannot prove the true upstream provider or model.

### Differential mode

The relay and official provider are both available. This enables stronger model identity and parameter compliance checks.

### Attested mode

Provider logs, billing data, request IDs, or signed upstream responses are available. This is required for high-confidence direct-forwarding claims.

## Core suites

| Suite | Purpose |
|---|---|
| request integrity | Detect visible request/response mutation through nonce echo and exact-output checks. |
| parameter override | Detect ignored or overwritten max_tokens, stop, JSON mode, and related fields. |
| model identity | Detect reported model mismatch and support later behavior fingerprinting. |
| hidden prompt | Detect unexpected prefixes, policy text, or refusal text in exact-output tasks. |
| stream protocol | Capture SSE lines and check whether stream framing resembles the expected protocol. |
| cache detection | Use unique nonces to detect response reuse across near-duplicate prompts. |
| guardrail redaction | Use synthetic fake secrets to detect redaction or filtering middleware. |
| usage consistency | Check local consistency of prompt_tokens, completion_tokens, and total_tokens. |

## Required evidence capture

Each run stores:

- run metadata
- target metadata without API keys
- canonical request body hash
- synthetic request body
- response status code
- parsed JSON response where available
- raw response body
- SSE event lines
- timing
- findings and severity

## Result states

- pass: expected observable behavior was present
- suspect: observable behavior suggests modification, downgrade, cache reuse, filtering, or inconsistent accounting
- fail: request/protocol failure invalidated the case
- inconclusive: not enough evidence
- info: useful evidence only

## Safety constraints

- Use synthetic prompts only.
- Never commit .env, API keys, raw customer prompts, or production reports.
- Do not treat model self-identification as strong evidence.
- Do not claim end-to-end response integrity without upstream attestation.

