from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from . import __version__
from .local_config import detect_local_config, detect_targets_raw, redact_secret
from .runner import Runner, write_report
from .schemas import Target
from .selftest import render_self_test_human, run_self_tests, write_self_test_report
from .transport import MockTransport, StdlibHTTPTransport


PROBE_STATUS_LABELS = {
    "pass": "PASS / 通过",
    "suspect": "SUSPECT / 可疑",
    "fail": "FAIL / 失败",
    "inconclusive": "INCONCLUSIVE / 证据不足",
    "info": "INFO / 信息",
}

ROUTE_LABELS = {
    "official_account_login_likely": "官方账号登录倾向",
    "official_api_key": "官方 API Key",
    "official_api_key_default_endpoint_likely": "官方默认端点 + API Key 倾向",
    "official_cloud_api": "官方云 API",
    "third_party_api": "三方 API / 中转",
    "local_switcher_or_proxy": "本地 CCswitch / 代理",
    "official_endpoint_configured": "官方端点已配置",
    "unknown": "未知 / 证据不足",
}

LOCAL_SWITCHER_LABELS = {
    "reachable": "reachable / 本地 API 已响应",
    "configured_but_unreachable": "configured_but_unreachable / 已配置但本地未响应",
    "configured_not_probed": "configured_not_probed / 已配置但未探测",
    "config_detected_no_local_url": "config_detected_no_local_url / 发现配置但未发现本地地址",
    "not_detected": "not_detected / 未发现",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="relayprobe", description="Audit OpenAI-compatible API relays.")
    parser.add_argument("--version", action="version", version=f"relayprobe {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Show local environment diagnostics.")
    sub.add_parser("list-suites", help="List available suites.")

    self_test = sub.add_parser("self-test", help="Run relayprobe unit tests with human-readable itemized output.")
    self_test.add_argument("--out", default="artifacts/self-test", help="Output directory for self-test report files.")
    self_test.add_argument("--no-write", action="store_true", help="Print only; do not write report files.")

    quickstart = sub.add_parser("quickstart", help="Run self-test, mock probes, and local detection in one command.")
    quickstart.add_argument("--out", default="", help="Output directory. Defaults to artifacts/quickstart-<timestamp>.")
    quickstart.add_argument("--no-probe-local", action="store_true", help="Do not probe detected localhost/loopback switcher URLs during local detection.")
    quickstart.add_argument("--run-detected-live", dest="run_detected_live", action="store_true", default=True, help="Use a detected local OpenAI-compatible API key/base URL/model for one live synthetic probe run. This is the quickstart default.")
    quickstart.add_argument("--no-run-detected-live", dest="run_detected_live", action="store_false", help="Skip the live detected API probe and run only local self-tests, mocks, and local route detection.")
    quickstart.add_argument("--model-fallback", default="gpt-4o", help="Model to use if a live detected target has no model.")

    run = sub.add_parser("run", help="Run the core probe suite.")
    run.add_argument("--target-name", default="relay", help="Display name for the target.")
    run.add_argument("--base-url", default=os.getenv("RELAYPROBE_BASE_URL", ""), help="Relay base URL, for example https://relay.example.com")
    run.add_argument("--model", default=os.getenv("RELAYPROBE_MODEL", "gpt-4o"), help="Requested model name.")
    run.add_argument("--api-key-env", default="RELAYPROBE_API_KEY", help="Environment variable containing the API key.")
    run.add_argument("--endpoint", default="/v1/chat/completions", help="OpenAI-compatible endpoint path.")
    run.add_argument(
        "--mock",
        choices=["clean", "tampered", "bad_stream", "redact", "cache", "downrank", "bad_usage"],
        help="Use deterministic local mock transport instead of live API.",
    )
    run.add_argument("--out", default="", help="Output directory. Defaults to artifacts/<run-id-like timestamp>.")

    report = sub.add_parser("report", help="Print a compact summary from report.json.")
    report.add_argument("path", help="Path to report.json")

    detect = sub.add_parser("detect-local", help="Detect local Codex/Claude Code/CC switch API configuration with redaction.")
    detect.add_argument("--out", default="artifacts/local-detect", help="Output directory for the redacted local detection report.")
    detect.add_argument("--no-write", action="store_true", help="Print only; do not write report.json.")
    detect.add_argument("--no-probe-local", action="store_true", help="Do not probe detected localhost/loopback switcher URLs.")
    detect.add_argument("--run-first", action="store_true", help="Run the core suite against the first detected OpenAI-compatible env target. This sends synthetic prompts to that configured API.")
    detect.add_argument("--run-detected-live", action="store_true", help="Explicitly use a detected local OpenAI-compatible API key/base URL/model from env or config files for one live synthetic probe run. This may incur API cost.")
    detect.add_argument("--model-fallback", default="gpt-4o", help="Model to use if a runnable target has no detected model.")

    args = parser.parse_args(argv)

    if args.command == "doctor":
        return _doctor()
    if args.command == "list-suites":
        return _list_suites()
    if args.command == "self-test":
        return _self_test(args)
    if args.command == "quickstart":
        return _quickstart(args)
    if args.command == "run":
        return _run(args)
    if args.command == "report":
        return _report(args.path)
    if args.command == "detect-local":
        return _detect_local(args)
    parser.error("unknown command")
    return 2


def _doctor() -> int:
    print(f"relayprobe {__version__}")
    print(f"python {sys.version.split()[0]}")
    print("runtime dependencies: standard library only")
    print("quickstart live API calls: enabled by default when a detected local key/base URL/model is available")
    return 0


def _list_suites() -> int:
    print("core")
    print("  request_integrity, param_override, hidden_prompt, stream_protocol, cache_detection, guardrail_redaction, usage_consistency, model_identity")
    return 0


def _self_test(args: argparse.Namespace) -> int:
    report = run_self_tests()
    if not args.no_write:
        json_path, text_path = write_self_test_report(report, args.out)
        print(f"wrote {json_path}")
        print(f"wrote {text_path}")
    print(render_self_test_human(report))
    return 0 if report["summary"].get("successful") else 1


def _quickstart(args: argparse.Namespace) -> int:
    run_id = time.strftime("quickstart-%Y%m%d-%H%M%S")
    out_dir = Path(args.out) if args.out else Path("artifacts") / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n=== relayprobe 一键跑通 / Quickstart ===")
    print(f"输出目录 output: {out_dir}")

    exit_code = 0

    print("\n[1/4] 项目自检 / Self-test")
    self_report = run_self_tests()
    write_self_test_report(self_report, out_dir / "self-test")
    print(render_self_test_human(self_report))
    if not self_report["summary"].get("successful"):
        exit_code = 1

    print("\n[2/4] 正常中转模拟 / Mock clean")
    clean_report = _run_mock_suite("clean")
    write_report(clean_report, out_dir / "mock-clean")
    _print_probe_report(clean_report)
    if clean_report["summary"].get("fail", 0) or clean_report["summary"].get("suspect", 0):
        exit_code = 1

    print("\n[3/4] 篡改中转模拟 / Mock tampered")
    tampered_report = _run_mock_suite("tampered")
    write_report(tampered_report, out_dir / "mock-tampered")
    _print_probe_report(tampered_report)

    print("\n[4/4] 本地 Codex / Claude Code / CCswitch 路由检测")
    local_report = detect_local_config(probe_local=not args.no_probe_local)
    local_dir = out_dir / "local-detect"
    local_dir.mkdir(parents=True, exist_ok=True)
    (local_dir / "report.json").write_text(json.dumps(local_report, ensure_ascii=False, indent=2), encoding="utf-8")
    _print_local_report(local_report)

    if args.run_detected_live:
        print("\n[extra] 真实本机配置 API 合成探针 / Live detected API probe")
        _run_detected_live_probe(
            out_dir / "live-detected",
            args.model_fallback,
            missing_is_error=False,
            fail_is_error=False,
        )

    print("\n=== 一键跑通完成 / Quickstart finished ===")
    print(f"报告目录: {out_dir}")
    if args.run_detected_live:
        print(f"真实配置合成探针报告目录: {out_dir / 'live-detected'}")
    else:
        print("已跳过真实配置合成探针。")
    return exit_code


def _run_mock_suite(mode: str) -> dict[str, Any]:
    target = Target(name="relay", base_url="mock://relayprobe", model="gpt-4o")
    return Runner(target, MockTransport(mode)).run_core()


def _run(args: argparse.Namespace) -> int:
    if args.mock:
        transport = MockTransport(args.mock)
        base_url = "mock://relayprobe"
        api_key = None
    else:
        if not args.base_url:
            print("error: --base-url is required for live runs unless --mock is used", file=sys.stderr)
            return 2
        api_key = os.getenv(args.api_key_env)
        if not api_key:
            print(f"error: API key environment variable is empty: {args.api_key_env}", file=sys.stderr)
            return 2
        transport = StdlibHTTPTransport()
        base_url = args.base_url

    target = Target(
        name=args.target_name,
        base_url=base_url,
        model=args.model,
        api_key=api_key,
        endpoint=args.endpoint,
    )
    runner = Runner(target, transport)
    report = runner.run_core()
    out_dir = args.out or str(Path("artifacts") / report["run"]["id"])
    json_path, markdown_path = write_report(report, out_dir)
    print(f"wrote {json_path}")
    print(f"wrote {markdown_path}")
    _print_probe_report(report)
    return 1 if report["summary"].get("fail", 0) else 0


def _report(path: str) -> int:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    _print_probe_report(data)
    return 0


def _detect_local(args: argparse.Namespace) -> int:
    report = detect_local_config(probe_local=not args.no_probe_local)
    out_dir = Path(args.out)
    if not args.no_write:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _print_local_report(report)

    if args.run_first:
        raw_targets = [target for target in detect_targets_raw() if target.runnable_openai_compatible()]
        if not raw_targets:
            print("no runnable OpenAI-compatible env target found; detect-local did not send any network request")
            return 1
        selected = raw_targets[0]
        model = selected.model or args.model_fallback
        print("running synthetic probe against detected target: " + selected.name + " model=" + model)
        runner = Runner(
            Target(
                name="detected:" + selected.name,
                base_url=selected.base_url or "",
                model=model,
                api_key=selected.api_key,
            ),
            StdlibHTTPTransport(),
        )
        probe_report = runner.run_core()
        probe_dir = out_dir / "probe"
        write_report(probe_report, probe_dir)
        _print_probe_report(probe_report)
    if args.run_detected_live:
        return _run_detected_live_probe(out_dir / "live-detected", args.model_fallback)
    return 0


def _run_detected_live_probe(
    out_dir: Path,
    model_fallback: str,
    missing_is_error: bool = True,
    fail_is_error: bool = True,
) -> int:
    raw_targets = detect_targets_raw(include_file_secrets=True)
    runnable = [target for target in raw_targets if target.runnable_openai_compatible()]
    if not runnable:
        print("未找到可直接运行的 OpenAI-compatible 本地配置目标；没有发送任何真实 API 请求。")
        return 1 if missing_is_error else 0

    selected = runnable[0]
    model = selected.model or model_fallback
    print(f"目标 target: {selected.name}")
    print(f"来源 source: {selected.source}")
    print(f"地址 base_url: {selected.base_url}")
    print(f"模型 model: {model}")
    print(f"Key 字段 key_name: {selected.api_key_name}")
    print(f"Key 脱敏 key_redacted: {redact_secret(selected.api_key)}")

    runner = Runner(
        Target(
            name="detected-live:" + selected.name,
            base_url=selected.base_url or "",
            model=model,
            api_key=selected.api_key,
        ),
        StdlibHTTPTransport(),
    )
    probe_report = runner.run_core()
    write_report(probe_report, out_dir)
    _print_probe_report(probe_report)
    return 1 if fail_is_error and probe_report["summary"].get("fail", 0) else 0


def _status_label(status: str) -> str:
    return PROBE_STATUS_LABELS.get(status, status.upper())


def _route_label(route_type: str | None) -> str:
    if not route_type:
        return ROUTE_LABELS["unknown"]
    return f"{route_type} / {ROUTE_LABELS.get(route_type, '未收录状态')}"


def _confidence_label(confidence: str | None) -> str:
    mapping = {"high": "high / 高", "medium": "medium / 中", "low": "low / 低"}
    return mapping.get(confidence or "", str(confidence))


def _print_probe_report(report: dict[str, Any]) -> None:
    summary = report.get("summary", {})
    target = report.get("target", {})
    print("\n=== relayprobe 探针运行结果 / Probe results ===")
    if isinstance(target, dict):
        print(f"测试目标 target: {target.get('name')}")
        print(f"请求模型 model: {target.get('model')}")
        print(f"API 地址 base_url: {target.get('base_url')}")
    if isinstance(summary, dict):
        print(
            "汇总 summary: "
            + f"total={summary.get('total', 0)}, "
            + f"pass={summary.get('pass', 0)}, "
            + f"suspect={summary.get('suspect', 0)}, "
            + f"fail={summary.get('fail', 0)}, "
            + f"inconclusive={summary.get('inconclusive', 0)}, "
            + f"info={summary.get('info', 0)}"
        )
    print("\n逐项检测明细 / Case details:")
    results = report.get("results", [])
    if not isinstance(results, list) or not results:
        print("  未找到 results。")
        return
    for index, result in enumerate(results, start=1):
        if not isinstance(result, dict):
            continue
        status = str(result.get("status", "unknown"))
        print(f"{index:02d}. [{_status_label(status)}] {result.get('case_id')}")
        print(f"    测试内容: {result.get('description')}")
        print(f"    检测类别: {result.get('category')}")
        findings = result.get("findings", [])
        if isinstance(findings, list):
            for finding in findings:
                if isinstance(finding, dict):
                    finding_status = str(finding.get("status", status))
                    print(f"    - {_status_label(finding_status)}: {finding.get('message')}")


def _print_local_report(report: dict[str, Any]) -> None:
    summary = report.get("summary", {})
    print("\n=== 本地 API 配置检测 / Local API route detection ===")
    if isinstance(summary, dict):
        print(
            "汇总 summary: "
            + f"targets={summary.get('targets', 0)}, "
            + f"config_files={summary.get('config_files_found', 0)}, "
            + f"env_values={summary.get('interesting_env_values', 0)}, "
            + f"codex_route={summary.get('codex_route_type')}, "
            + f"claude_code_route={summary.get('claude_code_route_type')}, "
            + f"local_switcher={summary.get('local_switcher_status')}"
        )

    print("\n1) 检测到的配置目标 / Detected targets")
    targets = report.get("targets", [])
    if not isinstance(targets, list) or not targets:
        print("  未发现 Codex/Claude/CCswitch 相关 API 配置。")
    else:
        for index, target in enumerate(targets, start=1):
            if not isinstance(target, dict):
                continue
            key_text = "未发现 Key"
            if target.get("api_key_present"):
                key_text = "发现 Key（已脱敏）: " + str(target.get("api_key_redacted"))
            elif target.get("api_key_name"):
                key_text = "配置文件中发现 Key 字段（不明文展示）: " + str(target.get("api_key_name"))
            print(f"  {index:02d}. {target.get('name')} / {target.get('provider_hint')}")
            print(f"      协议 protocol: {target.get('protocol')}")
            print(f"      地址 base_url: {target.get('base_url')}")
            print(f"      模型 model: {target.get('model')}")
            print(f"      Key 状态: {key_text}")
            print(f"      可直接跑 OpenAI-compatible 探针: {target.get('runnable_openai_compatible')}")

    assessment = report.get("assessment", {})
    clients = assessment.get("clients", []) if isinstance(assessment, dict) else []
    print("\n2) Codex / Claude Code 路由判断")
    if isinstance(clients, list):
        for client in clients:
            if not isinstance(client, dict):
                continue
            print(f"  - {client.get('client')}")
            print(f"      路由类型 route: {_route_label(str(client.get('route_type')))}")
            print(f"      置信度 confidence: {_confidence_label(str(client.get('confidence')))}")
            print(f"      认证方式 auth: {client.get('auth_mode')}")
            print(f"      地址 base_url: {client.get('base_url')}")
            print(f"      模型 model: {client.get('model')}")
            evidence = client.get("evidence", [])
            if isinstance(evidence, list) and evidence:
                print("      证据 evidence:")
                for item in evidence[:5]:
                    print(f"        - {item}")

    local_switcher = assessment.get("local_switcher", {}) if isinstance(assessment, dict) else {}
    print("\n3) 本地 CCswitch / 本地代理检测")
    if isinstance(local_switcher, dict):
        status = str(local_switcher.get("status"))
        print(f"  状态 status: {LOCAL_SWITCHER_LABELS.get(status, status)}")
        urls = local_switcher.get("configured_local_base_urls", [])
        print("  本地地址 urls: " + (json.dumps(urls, ensure_ascii=False) if urls else "未发现"))
        probes = local_switcher.get("probes", [])
        if isinstance(probes, list) and probes:
            for probe in probes:
                if isinstance(probe, dict):
                    print(f"  探测 probe: base_url={probe.get('base_url')} reachable={probe.get('reachable')} status_code={probe.get('status_code')}")

    print("\n4) 实际使用的中转 / Final active route summary")
    if isinstance(clients, list):
        for client in clients:
            if not isinstance(client, dict):
                continue
            name = client.get("client")
            route_type = str(client.get("route_type"))
            base_url = client.get("base_url") or "未检测到明确地址"
            model = client.get("model") or "未检测到明确模型"
            print(f"  - {name}: {_route_label(route_type)}")
            print(f"      实际地址: {base_url}")
            print(f"      实际模型: {model}")


if __name__ == "__main__":
    raise SystemExit(main())
