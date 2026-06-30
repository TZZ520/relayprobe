from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
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

    args = parser.parse_args(argv)

    if args.command == "doctor":
        return _doctor()
    if args.command == "list-suites":
        return _list_suites()
    if args.command == "run":
        return _run(args)
    if args.command == "report":
        return _report(args.path)
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


if __name__ == "__main__":
    raise SystemExit(main())

