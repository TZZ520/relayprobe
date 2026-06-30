from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from .schemas import Target, TransportResponse
from .util import chat_content, extract_tag


class Transport:
    def send(self, target: Target, body: dict[str, Any], stream: bool = False) -> TransportResponse:
        raise NotImplementedError


class StdlibHTTPTransport(Transport):
    """Small OpenAI-compatible HTTP transport using only the Python standard library."""

    def __init__(self, timeout_seconds: int = 60) -> None:
        self.timeout_seconds = timeout_seconds

    def send(self, target: Target, body: dict[str, Any], stream: bool = False) -> TransportResponse:
        url = join_base_and_endpoint(target.base_url, target.endpoint)
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if stream else "application/json",
            **target.extra_headers,
        }
        if target.api_key:
            headers["Authorization"] = f"Bearer {target.api_key}"

        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw_bytes = response.read()
                raw_text = raw_bytes.decode("utf-8", errors="replace")
                response_headers = {k.lower(): v for k, v in response.headers.items()}
                return _build_transport_response(response.status, raw_text, response_headers, stream)
        except urllib.error.HTTPError as exc:
            raw_text = exc.read().decode("utf-8", errors="replace")
            response_headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
            parsed = _try_json(raw_text)
            return TransportResponse(
                status_code=exc.code,
                response_json=parsed if isinstance(parsed, dict) else None,
                raw_response=raw_text,
                response_headers=response_headers,
                sse_events=_extract_sse_events(raw_text),
                error=str(exc),
            )
        except Exception as exc:
            return TransportResponse(
                status_code=0,
                response_json=None,
                raw_response="",
                response_headers={},
                sse_events=[],
                error=str(exc),
            )


def join_base_and_endpoint(base_url: str, endpoint: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1") and endpoint.startswith("/v1/"):
        return base + endpoint.removeprefix("/v1")
    return base + endpoint


class MockTransport(Transport):
    """Deterministic local transport for tests and demos."""

    def __init__(self, mode: str = "clean") -> None:
        self.mode = mode
        self._cached_content: str | None = None

    def send(self, target: Target, body: dict[str, Any], stream: bool = False) -> TransportResponse:
        time.sleep(0.001)
        messages = body.get("messages", [])
        prompt = chat_content(messages) if isinstance(messages, list) else ""
        requested_model = body.get("model", target.model)
        reported_model = "gpt-4o-mini" if self.mode in {"tampered", "downrank"} else requested_model

        if stream:
            return self._stream_response(reported_model)

        content = self._content_for(prompt, body)
        completion_tokens = max(1, min(64, len(content.split()) or len(content) // 4 or 1))
        prompt_tokens = max(1, len(prompt) // 4)
        total_tokens = prompt_tokens + completion_tokens
        if self.mode in {"tampered", "bad_usage"}:
            total_tokens += 17

        payload: dict[str, Any] = {
            "id": "chatcmpl-relayprobe-mock",
            "object": "chat.completion",
            "created": 1782780000,
            "model": reported_model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
        }
        return TransportResponse(
            status_code=200,
            response_json=payload,
            raw_response=json.dumps(payload, ensure_ascii=False),
            response_headers={"content-type": "application/json"},
        )

    def _stream_response(self, reported_model: str) -> TransportResponse:
        payload = {
            "id": "chatcmpl-relayprobe-stream",
            "object": "chat.completion.chunk",
            "model": reported_model,
            "choices": [{"index": 0, "delta": {"content": "stream-ok"}, "finish_reason": None}],
        }
        if self.mode in {"tampered", "bad_stream"}:
            raw = json.dumps({"message": "not really an SSE stream", "model": reported_model})
            return TransportResponse(
                status_code=200,
                response_json={"message": "not really an SSE stream", "model": reported_model},
                raw_response=raw,
                response_headers={"content-type": "application/json"},
                sse_events=[],
            )
        event = "data: " + json.dumps(payload, ensure_ascii=False)
        raw = event + "\n\ndata: [DONE]\n\n"
        return TransportResponse(
            status_code=200,
            response_json=payload,
            raw_response=raw,
            response_headers={"content-type": "text/event-stream"},
            sse_events=[event, "data: [DONE]"],
        )

    def _content_for(self, prompt: str, body: dict[str, Any]) -> str:
        echo_nonce = extract_tag(prompt, "RELAYPROBE_ECHO_NONCE")
        exact_marker = extract_tag(prompt, "RELAYPROBE_EXACT_OUTPUT")
        cache_nonce = extract_tag(prompt, "RELAYPROBE_CACHE_NONCE")
        json_nonce = extract_tag(prompt, "RELAYPROBE_JSON_NONCE")
        secret = extract_tag(prompt, "RELAYPROBE_FAKE_SECRET")

        if echo_nonce:
            return echo_nonce

        if exact_marker:
            if self.mode == "tampered":
                return f"Safety note: {exact_marker}"
            return exact_marker

        if body.get("max_tokens") == 1:
            if self.mode == "tampered":
                return "HELLO WORLD PARAMETER IGNORED"
            return "H"

        if "<RP_STOP>" in prompt:
            if self.mode == "tampered":
                return "ALPHA<RP_STOP>BETA"
            return "ALPHA"

        if json_nonce:
            if self.mode == "tampered":
                return f"relayprobe true nonce {json_nonce}"
            return json.dumps({"relayprobe": True, "nonce": json_nonce}, ensure_ascii=False)

        if cache_nonce:
            content = f"cache-nonce={cache_nonce}"
            if self.mode in {"tampered", "cache"}:
                if self._cached_content is None:
                    self._cached_content = content
                return self._cached_content
            return content

        if secret:
            if self.mode in {"tampered", "redact"}:
                return "The synthetic secret is [REDACTED]."
            return secret

        return "relayprobe-ok"


def _build_transport_response(
    status_code: int, raw_text: str, response_headers: dict[str, str], stream: bool
) -> TransportResponse:
    sse_events = _extract_sse_events(raw_text)
    parsed = _try_json(raw_text)
    response_json = parsed if isinstance(parsed, dict) else None
    if stream and response_json is None:
        response_json = _last_json_from_sse(sse_events)
    return TransportResponse(
        status_code=status_code,
        response_json=response_json,
        raw_response=raw_text,
        response_headers=response_headers,
        sse_events=sse_events,
    )


def _try_json(raw_text: str) -> Any | None:
    try:
        return json.loads(raw_text)
    except Exception:
        return None


def _extract_sse_events(raw_text: str) -> list[str]:
    events: list[str] = []
    for line in raw_text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            events.append(line)
    return events


def _last_json_from_sse(events: list[str]) -> dict[str, Any] | None:
    for event in reversed(events):
        data = event.removeprefix("data:").strip()
        if data == "[DONE]":
            continue
        parsed = _try_json(data)
        if isinstance(parsed, dict):
            return parsed
    return None
