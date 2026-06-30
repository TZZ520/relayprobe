from __future__ import annotations

from typing import Any

from .schemas import PreparedRequest, Probe
from .util import nonce


def build_core_suite(model: str) -> list[Probe]:
    echo = nonce("echo")
    exact = nonce("exact")
    json_nonce = nonce("json")
    cache_a = nonce("cache")
    cache_b = nonce("cache")
    fake_secret = "sk-relayprobe-fake-" + nonce("secret")

    return [
        Probe(
            case_id="request_integrity.echo_nonce",
            category="request_integrity",
            description="Response should echo a unique synthetic nonce exactly.",
            requests=[
                PreparedRequest(
                    "echo",
                    _chat_body(
                        model,
                        f"RELAYPROBE_ECHO_NONCE:{echo}\nReturn exactly this nonce and nothing else.",
                        temperature=0,
                        max_tokens=32,
                    ),
                )
            ],
            analyzer="echo_nonce",
        ),
        Probe(
            case_id="hidden_prompt.exact_output",
            category="hidden_prompt",
            description="Detect extra prefix/suffix text that may come from hidden instructions or response rewriting.",
            requests=[
                PreparedRequest(
                    "exact",
                    _chat_body(
                        model,
                        f"RELAYPROBE_EXACT_OUTPUT:{exact}\nReturn exactly the marker after RELAYPROBE_EXACT_OUTPUT and nothing else.",
                        temperature=0,
                        max_tokens=32,
                    ),
                )
            ],
            analyzer="exact_output",
        ),
        Probe(
            case_id="param.max_tokens",
            category="param_override",
            description="max_tokens=1 should strongly constrain the completion length.",
            requests=[
                PreparedRequest(
                    "max_tokens",
                    _chat_body(model, "Return the word HELLO.", temperature=0, max_tokens=1),
                )
            ],
            analyzer="max_tokens",
        ),
        Probe(
            case_id="param.stop_sequence",
            category="param_override",
            description="Stop sequence should prevent trailing marker text from appearing.",
            requests=[
                PreparedRequest(
                    "stop",
                    _chat_body(
                        model,
                        "Return exactly this text: ALPHA<RP_STOP>BETA",
                        temperature=0,
                        max_tokens=32,
                        stop=["<RP_STOP>"],
                    ),
                )
            ],
            analyzer="stop_sequence",
        ),
        Probe(
            case_id="param.json_object",
            category="param_override",
            description="JSON response format should produce parseable JSON object content.",
            requests=[
                PreparedRequest(
                    "json",
                    _chat_body(
                        model,
                        f"RELAYPROBE_JSON_NONCE:{json_nonce}\nJSON_ONLY. Return a JSON object with keys relayprobe=true and nonce.",
                        temperature=0,
                        max_tokens=128,
                        response_format={"type": "json_object"},
                    ),
                )
            ],
            analyzer="json_object",
        ),
        Probe(
            case_id="stream.openai_sse",
            category="stream_protocol",
            description="Streaming response should contain SSE data lines and a DONE marker.",
            requests=[
                PreparedRequest(
                    "stream",
                    _chat_body(model, "Stream one short token.", temperature=0, max_tokens=16, stream=True),
                    stream=True,
                )
            ],
            analyzer="stream_protocol",
        ),
        Probe(
            case_id="cache.nonce_pair",
            category="cache_detection",
            description="Near-duplicate prompts with different nonces should not reuse cached content.",
            requests=[
                PreparedRequest(
                    "cache_a",
                    _chat_body(
                        model,
                        f"RELAYPROBE_CACHE_NONCE:{cache_a}\nEcho only the cache nonce. This prompt is intentionally similar.",
                        temperature=0,
                        max_tokens=48,
                    ),
                ),
                PreparedRequest(
                    "cache_b",
                    _chat_body(
                        model,
                        f"RELAYPROBE_CACHE_NONCE:{cache_b}\nEcho only the cache nonce. This prompt is intentionally similar.",
                        temperature=0,
                        max_tokens=48,
                    ),
                ),
            ],
            analyzer="cache_nonce_pair",
        ),
        Probe(
            case_id="guardrail.synthetic_secret_echo",
            category="guardrail_redaction",
            description="Synthetic fake secret should be echoed exactly; redaction suggests guardrail middleware.",
            requests=[
                PreparedRequest(
                    "redaction",
                    _chat_body(
                        model,
                        f"RELAYPROBE_FAKE_SECRET:{fake_secret}\nThis is a fake synthetic test token. Echo it exactly.",
                        temperature=0,
                        max_tokens=80,
                    ),
                )
            ],
            analyzer="guardrail_redaction",
        ),
        Probe(
            case_id="usage.local_consistency",
            category="usage_consistency",
            description="Usage total should equal prompt_tokens plus completion_tokens.",
            requests=[
                PreparedRequest(
                    "usage",
                    _chat_body(model, "Reply with relayprobe-ok.", temperature=0, max_tokens=32),
                )
            ],
            analyzer="usage_consistency",
        ),
        Probe(
            case_id="model.reported_name",
            category="model_identity",
            description="Response model metadata should match the requested model; matching is not proof of true model.",
            requests=[
                PreparedRequest(
                    "model",
                    _chat_body(model, "Reply with relayprobe-ok.", temperature=0, max_tokens=32),
                )
            ],
            analyzer="reported_model",
        ),
    ]


def _chat_body(model: str, prompt: str, **params: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    body.update(params)
    return body

