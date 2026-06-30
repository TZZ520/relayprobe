from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Target:
    name: str
    base_url: str
    model: str
    api_key: str | None = None
    endpoint: str = "/v1/chat/completions"
    extra_headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PreparedRequest:
    request_id: str
    body: dict[str, Any]
    stream: bool = False


@dataclass
class TransportResponse:
    status_code: int
    response_json: dict[str, Any] | None
    raw_response: str
    response_headers: dict[str, str] = field(default_factory=dict)
    sse_events: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class RequestRecord:
    case_id: str
    request_id: str
    target_name: str
    endpoint: str
    request_body_sha256: str
    request_body: dict[str, Any]
    status_code: int
    raw_response: str
    response_json: dict[str, Any] | None
    response_headers: dict[str, str]
    sse_events: list[str]
    elapsed_ms: int
    error: str | None = None


@dataclass(frozen=True)
class Finding:
    status: str
    code: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class CaseResult:
    case_id: str
    category: str
    description: str
    status: str
    findings: list[Finding]
    records: list[RequestRecord]


@dataclass(frozen=True)
class Probe:
    case_id: str
    category: str
    description: str
    requests: list[PreparedRequest]
    analyzer: str

