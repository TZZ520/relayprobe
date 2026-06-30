from __future__ import annotations

import io
import json
import time
import unittest
from pathlib import Path
from typing import Any


STATUS_LABELS = {
    "pass": "PASS / 通过",
    "fail": "FAIL / 失败",
    "error": "ERROR / 错误",
    "skip": "SKIP / 跳过",
}


FRIENDLY_TESTS = {
    "test_clean_mock_has_no_suspect_or_fail": "干净 mock 中转：不应该出现可疑或失败结果。",
    "test_tampered_mock_detects_multiple_suspects": "被篡改 mock 中转：应该能检测出多项可疑行为。",
    "test_content_extraction": "响应内容提取：应能从 OpenAI-compatible 响应里取出文本。",
    "test_report_write_and_summary": "报告写入：应生成 JSON/Markdown 报告，并统计 10 个核心探针。",
    "test_bad_stream_is_suspect": "坏流式协议：伪造/异常 SSE 应被标记为可疑。",
    "test_redacts_secret_and_url_credentials": "脱敏规则：API Key、URL 用户名密码、URL query token 都不能明文展示。",
    "test_env_detection_keeps_raw_key_out_of_public_report": "环境变量检测：能发现 OpenAI/Codex 配置，但报告不能包含原始 Key。",
    "test_file_detection_is_redacted_and_not_runnable": "配置文件检测：能发现配置文件里的地址/模型/Key，但不会拿文件 Key 自动联网。",
    "test_file_secret_is_raw_only_for_explicit_live_opt_in": "真实 Key 使用边界：只有显式开启 live opt-in 时，配置文件 Key 才能在内存中用于本次测试。",
    "test_claude_auth_token_env_is_detected": "Claude Code/Anthropic 环境变量：能识别 auth token、base URL 和模型。",
    "test_route_assessment_distinguishes_third_party_and_local_switcher": "路由判断：能区分三方 API 和 localhost 本地 switcher/proxy。",
    "test_codex_auth_file_is_classified_as_official_account_login_likely": "Codex 官方账号登录痕迹：auth.json 存在时应标记为官方账号登录倾向。",
    "test_codex_config_does_not_drive_claude_route": "客户端隔离：Codex 配置不能误影响 Claude Code 路由判断。",
    "test_local_probe_candidates_never_include_url_credentials_or_query": "本地探测安全：探测 localhost 时不能带 URL 凭证或 query secret。",
    "test_join_base_and_endpoint_avoids_double_v1": "URL 拼接：base_url 已包含 /v1 时，真实请求不能变成 /v1/v1。",
}


class CollectingResult(unittest.TextTestResult):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.items: list[dict[str, Any]] = []

    def addSuccess(self, test: unittest.case.TestCase) -> None:
        super().addSuccess(test)
        self.items.append(test_item(test, "pass"))

    def addFailure(self, test: unittest.case.TestCase, err: tuple[type[BaseException], BaseException, Any]) -> None:
        super().addFailure(test, err)
        self.items.append(test_item(test, "fail", self._exc_info_to_string(err, test)))

    def addError(self, test: unittest.case.TestCase, err: tuple[type[BaseException], BaseException, Any]) -> None:
        super().addError(test, err)
        self.items.append(test_item(test, "error", self._exc_info_to_string(err, test)))

    def addSkip(self, test: unittest.case.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        self.items.append(test_item(test, "skip", reason))


def test_item(test: unittest.case.TestCase, status: str, detail: str | None = None) -> dict[str, Any]:
    test_id = test.id()
    method = test_id.split(".")[-1]
    return {
        "id": test_id,
        "name": method,
        "status": status,
        "status_label": STATUS_LABELS.get(status, status.upper()),
        "description_zh": FRIENDLY_TESTS.get(method, "项目自检测试项。"),
        "detail": detail,
    }


def run_self_tests(start_dir: str = "tests") -> dict[str, Any]:
    started = time.time()
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir)
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=CollectingResult)
    result = runner.run(suite)
    items = getattr(result, "items", [])
    summary = {
        "total": result.testsRun,
        "pass": sum(1 for item in items if item["status"] == "pass"),
        "fail": len(result.failures),
        "error": len(result.errors),
        "skip": len(result.skipped),
        "successful": result.wasSuccessful(),
    }
    return {
        "generated_at_epoch": int(time.time()),
        "elapsed_ms": int((time.time() - started) * 1000),
        "summary": summary,
        "tests": items,
        "raw_unittest_output": stream.getvalue(),
    }


def render_self_test_human(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "relayprobe 项目自检 / Self-test",
        "",
        f"总计 total: {summary['total']}",
        f"通过 pass: {summary['pass']}",
        f"失败 fail: {summary['fail']}",
        f"错误 error: {summary['error']}",
        f"跳过 skip: {summary['skip']}",
        f"整体状态 overall: {'PASS / 全部通过' if summary['successful'] else 'FAIL / 存在失败'}",
        "",
        "逐项结果 / Test items:",
    ]
    for index, item in enumerate(report["tests"], start=1):
        lines.append(f"{index:02d}. [{item['status_label']}] {item['name']}")
        lines.append(f"    测试内容: {item['description_zh']}")
        lines.append(f"    unittest id: {item['id']}")
        if item.get("detail"):
            lines.append(f"    详情: {item['detail']}")
    return "\n".join(lines)


def write_self_test_report(report: dict[str, Any], out_dir: str | Path) -> tuple[Path, Path]:
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    json_path = path / "report.json"
    text_path = path / "summary.txt"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    text_path.write_text(render_self_test_human(report), encoding="utf-8")
    return json_path, text_path
