from __future__ import annotations

import json
from typing import Callable

from .schemas import CaseResult, Finding, RequestRecord
from .util import chat_content, extract_tag


Analyzer = Callable[[str, str, str, list[RequestRecord]], CaseResult]


def analyze(case_id: str, category: str, description: str, analyzer_name: str, records: list[RequestRecord]) -> CaseResult:
    try:
        fn = ANALYZERS[analyzer_name]
    except KeyError as exc:
        raise ValueError(f"unknown analyzer: {analyzer_name}") from exc
    return fn(case_id, category, description, records)


def content(record: RequestRecord) -> str:
    data = record.response_json or {}
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message") or {}
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"]
            delta = first.get("delta") or {}
            if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                return delta["content"]
    if isinstance(data.get("content"), str):
        return data["content"]
    return ""


def _request_prompt(record: RequestRecord) -> str:
    messages = record.request_body.get("messages", [])
    return chat_content(messages) if isinstance(messages, list) else ""


def _single_record_guard(records: list[RequestRecord]) -> Finding | None:
    if not records:
        return Finding("fail", "no_records", "No request record was captured.")
    record = records[0]
    if record.error:
        return Finding("fail", "transport_error", "Transport returned an error.", {"error": record.error})
    if record.status_code < 200 or record.status_code >= 300:
        return Finding("fail", "http_error", "HTTP status was not successful.", {"status_code": record.status_code})
    return None


def echo_nonce(case_id: str, category: str, description: str, records: list[RequestRecord]) -> CaseResult:
    guard = _single_record_guard(records)
    if guard:
        return CaseResult(case_id, category, description, guard.status, [guard], records)
    record = records[0]
    expected = extract_tag(_request_prompt(record), "RELAYPROBE_ECHO_NONCE")
    got = content(record)
    if expected and got.strip() == expected:
        finding = Finding("pass", "nonce_echoed", "Response echoed the unique nonce exactly.", {"nonce": expected})
    else:
        finding = Finding(
            "suspect",
            "nonce_not_exact",
            "Response did not echo the unique nonce exactly; this can indicate prompt injection, filtering, or model noncompliance.",
            {"expected": expected, "content": got[:200]},
        )
    return CaseResult(case_id, category, description, finding.status, [finding], records)


def exact_output(case_id: str, category: str, description: str, records: list[RequestRecord]) -> CaseResult:
    guard = _single_record_guard(records)
    if guard:
        return CaseResult(case_id, category, description, guard.status, [guard], records)
    record = records[0]
    expected = extract_tag(_request_prompt(record), "RELAYPROBE_EXACT_OUTPUT")
    got = content(record).strip()
    if expected and got == expected:
        finding = Finding("pass", "exact_output", "Response matched the exact-output marker.")
    else:
        finding = Finding(
            "suspect",
            "unexpected_prefix_or_suffix",
            "Exact-output probe returned additional or changed text.",
            {"expected": expected, "content": got[:200]},
        )
    return CaseResult(case_id, category, description, finding.status, [finding], records)


def max_tokens(case_id: str, category: str, description: str, records: list[RequestRecord]) -> CaseResult:
    guard = _single_record_guard(records)
    if guard:
        return CaseResult(case_id, category, description, guard.status, [guard], records)
    record = records[0]
    got = content(record)
    completion_tokens = ((record.response_json or {}).get("usage") or {}).get("completion_tokens")
    if completion_tokens is not None and completion_tokens <= 1:
        finding = Finding("pass", "completion_token_limit_respected", "Reported completion_tokens respected max_tokens=1.")
    elif len(got) <= 4:
        finding = Finding("pass", "short_completion", "Completion was short enough for max_tokens=1.")
    else:
        finding = Finding(
            "suspect",
            "max_tokens_ignored",
            "Completion appears too long for max_tokens=1.",
            {"completion_tokens": completion_tokens, "content": got[:120]},
        )
    return CaseResult(case_id, category, description, finding.status, [finding], records)


def stop_sequence(case_id: str, category: str, description: str, records: list[RequestRecord]) -> CaseResult:
    guard = _single_record_guard(records)
    if guard:
        return CaseResult(case_id, category, description, guard.status, [guard], records)
    got = content(records[0])
    if "<RP_STOP>" in got or "BETA" in got:
        finding = Finding(
            "suspect",
            "stop_sequence_ignored",
            "Response contains content that should have been removed by the stop sequence.",
            {"content": got[:160]},
        )
    else:
        finding = Finding("pass", "stop_sequence_applied", "Response did not include the stop sequence or trailing marker.")
    return CaseResult(case_id, category, description, finding.status, [finding], records)


def json_object(case_id: str, category: str, description: str, records: list[RequestRecord]) -> CaseResult:
    guard = _single_record_guard(records)
    if guard:
        return CaseResult(case_id, category, description, guard.status, [guard], records)
    got = content(records[0]).strip()
    try:
        parsed = json.loads(got)
    except Exception:
        finding = Finding(
            "suspect",
            "json_mode_not_respected",
            "Response content was not valid JSON despite JSON response_format.",
            {"content": got[:200]},
        )
    else:
        if isinstance(parsed, dict):
            finding = Finding("pass", "valid_json_object", "Response content was valid JSON object.")
        else:
            finding = Finding("suspect", "json_not_object", "Response JSON was valid but not an object.", {"type": type(parsed).__name__})
    return CaseResult(case_id, category, description, finding.status, [finding], records)


def stream_protocol(case_id: str, category: str, description: str, records: list[RequestRecord]) -> CaseResult:
    guard = _single_record_guard(records)
    if guard:
        return CaseResult(case_id, category, description, guard.status, [guard], records)
    record = records[0]
    has_data = any(event.startswith("data:") for event in record.sse_events)
    has_done = any(event.strip() == "data: [DONE]" for event in record.sse_events)
    if has_data and has_done:
        finding = Finding("pass", "sse_framing_present", "Stream response contained SSE data lines and DONE marker.", {"events": record.sse_events[:5]})
    else:
        finding = Finding(
            "suspect",
            "sse_framing_missing",
            "Stream response did not contain expected SSE data lines and DONE marker.",
            {"content_type": record.response_headers.get("content-type"), "raw_preview": record.raw_response[:160]},
        )
    return CaseResult(case_id, category, description, finding.status, [finding], records)


def cache_nonce_pair(case_id: str, category: str, description: str, records: list[RequestRecord]) -> CaseResult:
    if len(records) != 2:
        finding = Finding("fail", "expected_two_records", "Cache probe requires exactly two request records.", {"count": len(records)})
        return CaseResult(case_id, category, description, finding.status, [finding], records)
    findings: list[Finding] = []
    nonces = [extract_tag(_request_prompt(record), "RELAYPROBE_CACHE_NONCE") for record in records]
    contents = [content(record) for record in records]
    if records[0].error or records[1].error:
        finding = Finding("fail", "transport_error", "One of the cache probe requests failed.")
        return CaseResult(case_id, category, description, finding.status, [finding], records)
    if nonces[0] and nonces[1] and nonces[0] != nonces[1]:
        if nonces[0] in contents[0] and nonces[1] in contents[1] and contents[0] != contents[1]:
            findings.append(Finding("pass", "unique_nonces_preserved", "Near-duplicate requests returned their own nonce."))
        else:
            findings.append(
                Finding(
                    "suspect",
                    "possible_cache_reuse",
                    "Near-duplicate requests did not preserve distinct nonces; possible semantic cache reuse or response rewriting.",
                    {"nonces": nonces, "contents": [c[:120] for c in contents]},
                )
            )
    else:
        findings.append(Finding("inconclusive", "nonce_setup_failed", "Cache probe did not create two distinct nonces.", {"nonces": nonces}))
    status = _worst_status(findings)
    return CaseResult(case_id, category, description, status, findings, records)


def guardrail_redaction(case_id: str, category: str, description: str, records: list[RequestRecord]) -> CaseResult:
    guard = _single_record_guard(records)
    if guard:
        return CaseResult(case_id, category, description, guard.status, [guard], records)
    record = records[0]
    expected = extract_tag(_request_prompt(record), "RELAYPROBE_FAKE_SECRET")
    got = content(record)
    if expected and got.strip() == expected:
        finding = Finding("pass", "synthetic_secret_echoed", "Synthetic fake secret was echoed exactly.")
    elif "REDACT" in got.upper() or "[REDACTED]" in got.upper():
        finding = Finding(
            "suspect",
            "redaction_observed",
            "Response appears redacted. This may indicate guardrail middleware or response rewriting.",
            {"expected": expected, "content": got[:160]},
        )
    else:
        finding = Finding(
            "inconclusive",
            "secret_not_echoed",
            "Synthetic fake secret was not echoed, but no explicit redaction marker was observed.",
            {"expected": expected, "content": got[:160]},
        )
    return CaseResult(case_id, category, description, finding.status, [finding], records)


def usage_consistency(case_id: str, category: str, description: str, records: list[RequestRecord]) -> CaseResult:
    guard = _single_record_guard(records)
    if guard:
        return CaseResult(case_id, category, description, guard.status, [guard], records)
    usage = ((records[0].response_json or {}).get("usage") or {})
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    total_tokens = usage.get("total_tokens")
    if not all(isinstance(v, int) for v in [prompt_tokens, completion_tokens, total_tokens]):
        finding = Finding("inconclusive", "usage_missing", "Usage fields are missing or not integers.", {"usage": usage})
    elif prompt_tokens + completion_tokens == total_tokens:
        finding = Finding("pass", "usage_totals_consistent", "Usage total equals prompt_tokens + completion_tokens.", {"usage": usage})
    else:
        finding = Finding(
            "suspect",
            "usage_totals_inconsistent",
            "Usage total does not equal prompt_tokens + completion_tokens.",
            {"usage": usage},
        )
    return CaseResult(case_id, category, description, finding.status, [finding], records)


def reported_model(case_id: str, category: str, description: str, records: list[RequestRecord]) -> CaseResult:
    guard = _single_record_guard(records)
    if guard:
        return CaseResult(case_id, category, description, guard.status, [guard], records)
    record = records[0]
    requested = record.request_body.get("model")
    reported = (record.response_json or {}).get("model")
    if reported == requested:
        finding = Finding(
            "info",
            "reported_model_matches",
            "Response model field matches the request. This is useful metadata but not proof of true upstream model.",
            {"requested": requested, "reported": reported},
        )
    else:
        finding = Finding(
            "suspect",
            "reported_model_mismatch",
            "Response model field differs from requested model.",
            {"requested": requested, "reported": reported},
        )
    return CaseResult(case_id, category, description, finding.status, [finding], records)


def _worst_status(findings: list[Finding]) -> str:
    order = {"fail": 4, "suspect": 3, "inconclusive": 2, "info": 1, "pass": 0}
    return max(findings, key=lambda finding: order.get(finding.status, 0)).status if findings else "inconclusive"


ANALYZERS: dict[str, Analyzer] = {
    "echo_nonce": echo_nonce,
    "exact_output": exact_output,
    "max_tokens": max_tokens,
    "stop_sequence": stop_sequence,
    "json_object": json_object,
    "stream_protocol": stream_protocol,
    "cache_nonce_pair": cache_nonce_pair,
    "guardrail_redaction": guardrail_redaction,
    "usage_consistency": usage_consistency,
    "reported_model": reported_model,
}

