from __future__ import annotations

import json
import os
import platform
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from . import __version__
from .analyzers import analyze
from .cases import build_core_suite
from .schemas import CaseResult, RequestRecord, Target
from .transport import Transport
from .util import canonical_json, request_hash


class Runner:
    def __init__(self, target: Target, transport: Transport) -> None:
        self.target = target
        self.transport = transport

    def run_core(self) -> dict[str, Any]:
        run_id = time.strftime("relayprobe-%Y%m%d-%H%M%S")
        started = time.time()
        results: list[CaseResult] = []
        for probe in build_core_suite(self.target.model):
            records: list[RequestRecord] = []
            for request in probe.requests:
                before = time.perf_counter()
                response = self.transport.send(self.target, request.body, stream=request.stream)
                elapsed_ms = int((time.perf_counter() - before) * 1000)
                records.append(
                    RequestRecord(
                        case_id=probe.case_id,
                        request_id=request.request_id,
                        target_name=self.target.name,
                        endpoint=self.target.endpoint,
                        request_body_sha256=request_hash(request.body),
                        request_body=request.body,
                        status_code=response.status_code,
                        raw_response=response.raw_response,
                        response_json=response.response_json,
                        response_headers=response.response_headers,
                        sse_events=response.sse_events,
                        elapsed_ms=elapsed_ms,
                        error=response.error,
                    )
                )
            results.append(analyze(probe.case_id, probe.category, probe.description, probe.analyzer, records))

        report = {
            "run": {
                "id": run_id,
                "relayprobe_version": __version__,
                "started_at_epoch": int(started),
                "elapsed_ms": int((time.time() - started) * 1000),
                "python": platform.python_version(),
                "platform": platform.platform(),
            },
            "target": {
                "name": self.target.name,
                "base_url": self.target.base_url,
                "model": self.target.model,
                "endpoint": self.target.endpoint,
                "api_key_present": bool(self.target.api_key),
            },
            "summary": summarize(results),
            "results": [_case_result_to_dict(result) for result in results],
        }
        return report


def summarize(results: list[CaseResult]) -> dict[str, int]:
    counts = {"pass": 0, "suspect": 0, "fail": 0, "inconclusive": 0, "info": 0}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    counts["total"] = len(results)
    return counts


def write_report(report: dict[str, Any], out_dir: str | os.PathLike[str]) -> tuple[Path, Path]:
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    json_path = path / "report.json"
    markdown_path = path / "summary.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# relayprobe report",
        "",
        f"- run id: {report['run']['id']}",
        f"- target: {report['target']['name']}",
        f"- model: {report['target']['model']}",
        f"- base url: {report['target']['base_url']}",
        "",
        "## Summary",
        "",
    ]
    for key in ["total", "pass", "suspect", "fail", "inconclusive", "info"]:
        lines.append(f"- {key}: {report['summary'].get(key, 0)}")
    lines.extend(["", "## Results", ""])
    for result in report["results"]:
        lines.append(f"### {result['case_id']}")
        lines.append("")
        lines.append(f"- status: {result['status']}")
        lines.append(f"- category: {result['category']}")
        for finding in result["findings"]:
            lines.append(f"- {finding['status']} / {finding['code']}: {finding['message']}")
        lines.append("")
    return "\n".join(lines)


def _case_result_to_dict(result: CaseResult) -> dict[str, Any]:
    data = asdict(result)
    for record in data["records"]:
        record["request_body_canonical"] = canonical_json(record["request_body"])
    return data

