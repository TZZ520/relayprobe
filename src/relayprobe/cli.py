from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .local_config import detect_local_config, detect_targets_raw
from .runner import Runner, write_report
from .schemas import Target
from .transport import MockTransport, StdlibHTTPTransport


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="relayprobe", description="Audit OpenAI-compatible API relays.")
    parser.add_argument("--version", action="version", version=f"relayprobe {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Show local environment diagnostics.")
    sub.add_parser("list-suites", help="List available suites.")

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
    detect.add_argument("--model-fallback", default="gpt-4o", help="Model to use if a runnable target has no detected model.")

    args = parser.parse_args(argv)

    if args.command == "doctor":
        return _doctor()
    if args.command == "list-suites":
        return _list_suites()
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
    print("live API calls: opt-in via relayprobe run --base-url ...")
    return 0


def _list_suites() -> int:
    print("core")
    print("  request_integrity, param_override, hidden_prompt, stream_protocol, cache_detection, guardrail_redaction, usage_consistency, model_identity")
    return 0


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
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    return 1 if report["summary"].get("fail", 0) else 0


def _report(path: str) -> int:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    print(json.dumps(data.get("summary", {}), ensure_ascii=False, indent=2, sort_keys=True))
    for result in data.get("results", []):
        print(f"{result['status']:12} {result['case_id']}")
    return 0


def _detect_local(args: argparse.Namespace) -> int:
    report = detect_local_config(probe_local=not args.no_probe_local)
    out_dir = Path(args.out)
    if not args.no_write:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))
    for target in report["targets"]:
        print(
            "target "
            + target["name"]
            + " protocol="
            + target["protocol"]
            + " base_url="
            + str(target["base_url"])
            + " model="
            + str(target["model"])
            + " key="
            + str(target["api_key_redacted"])
            + " runnable="
            + str(target["runnable_openai_compatible"])
        )
    assessment = report.get("assessment", {})
    for client in assessment.get("clients", []):
        print(
            "client "
            + client["client"]
            + " route="
            + client["route_type"]
            + " confidence="
            + client["confidence"]
            + " auth="
            + client["auth_mode"]
            + " base_url="
            + str(client.get("base_url"))
            + " model="
            + str(client.get("model"))
        )
    local_switcher = assessment.get("local_switcher", {})
    print(
        "local_switcher status="
        + str(local_switcher.get("status"))
        + " urls="
        + json.dumps(local_switcher.get("configured_local_base_urls", []), ensure_ascii=False)
    )

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
        print(json.dumps(probe_report["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
