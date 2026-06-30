from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from ipaddress import ip_address
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .util import sha256_text


SECRET_KEY_RE = re.compile(r"(api[_-]?key|auth[_-]?token|access[_-]?token|secret|password|authorization|bearer)", re.I)
BASE_URL_RE = re.compile(r"(base[_-]?url|api[_-]?base|endpoint|proxy[_-]?url|url)$", re.I)
MODEL_RE = re.compile(r"(model|default[_-]?model|model[_-]?name)$", re.I)
URL_SECRET_PARAM_RE = re.compile(r"(api[_-]?key|key|token|secret|password|auth|authorization)", re.I)
OPENAI_OFFICIAL_HOSTS = {"api.openai.com", "chatgpt.com", "chat.openai.com"}
ANTHROPIC_OFFICIAL_HOSTS = {"api.anthropic.com"}


ENV_CANDIDATES = {
    "codex/openai-compatible": {
        "api_key": ["OPENAI_API_KEY", "CODEX_API_KEY"],
        "base_url": ["OPENAI_BASE_URL", "OPENAI_API_BASE", "CODEX_BASE_URL", "CODEX_API_BASE"],
        "model": ["OPENAI_MODEL", "OPENAI_DEFAULT_MODEL", "CODEX_MODEL"],
        "protocol": "openai-compatible",
    },
    "claude-code/anthropic": {
        "api_key": ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_API_KEY", "CLAUDE_AUTH_TOKEN"],
        "base_url": ["ANTHROPIC_BASE_URL", "ANTHROPIC_API_URL", "CLAUDE_BASE_URL", "CLAUDE_API_BASE", "CLAUDE_CODE_BASE_URL"],
        "model": ["ANTHROPIC_MODEL", "ANTHROPIC_SMALL_FAST_MODEL", "CLAUDE_MODEL", "CLAUDE_CODE_MODEL"],
        "protocol": "anthropic-messages",
    },
    "azure-openai": {
        "api_key": ["AZURE_OPENAI_API_KEY"],
        "base_url": ["AZURE_OPENAI_ENDPOINT"],
        "model": ["AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_MODEL"],
        "protocol": "azure-openai",
    },
    "ccswitch/explicit": {
        "api_key": ["CCSWITCH_API_KEY", "CCSWITCH_AUTH_TOKEN"],
        "base_url": ["CCSWITCH_BASE_URL", "CCSWITCH_API_BASE", "CCSWITCH_ENDPOINT"],
        "model": ["CCSWITCH_MODEL", "CCSWITCH_DEFAULT_MODEL"],
        "protocol": "unknown",
    },
}


FILE_CANDIDATES = [
    ".codex/config.toml",
    ".codex/config.json",
    ".codex/auth.json",
    ".claude.json",
    ".claude/config.json",
    ".claude/settings.json",
    ".claude/settings.local.json",
    ".claude/.credentials.json",
    ".config/claude-code/config.json",
    ".config/ccswitch/config.json",
    ".ccswitch/config.json",
    ".claude-code-router/config.json",
]


@dataclass
class LocalValue:
    name: str
    value_kind: str
    value_redacted: str | None
    present: bool
    source_type: str
    source: str
    fingerprint8: str | None = None


@dataclass
class LocalTarget:
    name: str
    provider_hint: str
    protocol: str
    source: str
    api_key: str | None = None
    api_key_name: str | None = None
    base_url: str | None = None
    model: str | None = None
    notes: list[str] = field(default_factory=list)

    def runnable_openai_compatible(self) -> bool:
        return bool(self.api_key and self.base_url and self.protocol == "openai-compatible")

    def public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "provider_hint": self.provider_hint,
            "protocol": self.protocol,
            "source": self.source,
            "api_key_present": bool(self.api_key),
            "api_key_name": self.api_key_name,
            "api_key_redacted": redact_secret(self.api_key) if self.api_key else None,
            "api_key_fingerprint8": fingerprint8(self.api_key) if self.api_key else None,
            "base_url": redact_urlish(self.base_url),
            "model": self.model,
            "runnable_openai_compatible": self.runnable_openai_compatible(),
            "notes": self.notes,
        }


def redact_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "***"
    return value[:4] + "..." + value[-4:]


def fingerprint8(value: str | None) -> str | None:
    if not value:
        return None
    return sha256_text(value)[:8]


def redact_urlish(value: str | None) -> str | None:
    """Keep the useful endpoint identity while removing credentials embedded in a URL."""
    if not value:
        return value
    if "://" not in value:
        return value
    try:
        parts = urlsplit(value)
    except Exception:
        return value
    if not parts.scheme or not parts.netloc:
        return value

    try:
        host = parts.hostname or ""
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        if parts.port:
            host = f"{host}:{parts.port}"
    except ValueError:
        host = parts.netloc.split("@")[-1]

    netloc = host
    if parts.username or parts.password:
        netloc = "***@" + host if not parts.password else "***:***@" + host

    query_pairs = []
    for key, item_value in parse_qsl(parts.query, keep_blank_values=True):
        query_pairs.append((key, "***" if URL_SECRET_PARAM_RE.search(key) else item_value))
    query = urlencode(query_pairs, doseq=True, safe="*")
    fragment = "***" if parts.fragment and SECRET_KEY_RE.search(parts.fragment) else parts.fragment
    return urlunsplit((parts.scheme, netloc, parts.path, query, fragment))


def redact_value(kind: str, value: str) -> str:
    if kind == "secret":
        return redact_secret(value) or "***"
    if kind == "base_url":
        return redact_urlish(value) or ""
    return value


def detect_local_config(
    env: dict[str, str] | None = None,
    home: Path | None = None,
    appdata: Path | None = None,
    probe_local: bool = True,
) -> dict[str, Any]:
    env = dict(os.environ if env is None else env)
    home = Path.home() if home is None else home
    appdata = Path(env.get("APPDATA", "")) if appdata is None and env.get("APPDATA") else appdata

    values: list[LocalValue] = []
    targets: list[LocalTarget] = []

    for provider, spec in ENV_CANDIDATES.items():
        api_key_name, api_key = first_env(env, spec["api_key"])
        base_name, base_url = first_env(env, spec["base_url"])
        model_name, model = first_env(env, spec["model"])
        if api_key or base_url or model:
            target = LocalTarget(
                name=provider,
                provider_hint=provider,
                protocol=spec["protocol"],
                source="environment",
                api_key=api_key,
                api_key_name=api_key_name,
                base_url=base_url,
                model=model,
            )
            if model_name and not model:
                target.notes.append("model variable was present but empty")
            if base_name and not base_url:
                target.notes.append("base_url variable was present but empty")
            targets.append(target)

    for key, value in sorted(env.items()):
        if is_interesting_key(key):
            kind = classify_key(key)
            values.append(
                LocalValue(
                    name=key,
                    value_kind=kind,
                    value_redacted=redact_value(kind, value),
                    present=value != "",
                    source_type="env",
                    source="environment",
                    fingerprint8=fingerprint8(value) if kind == "secret" and value else None,
                )
            )

    file_results = []
    for path in candidate_paths(home, appdata, env):
        if not path.exists() or not path.is_file():
            continue
        extracted = extract_file_values(path)
        file_results.append(
            {
                "path": str(path),
                "exists": True,
                "values": [asdict(item) for item in extracted],
            }
        )
        targets.extend(targets_from_file(path, extracted))

    public_targets = [target.public_dict() for target in targets]
    assessment = assess_local_routes(targets, file_results, probe_local=probe_local)
    report = {
        "generated_at_epoch": int(time.time()),
        "policy": {
            "local_only": True,
            "network_upload": False,
            "secrets_redacted": True,
            "raw_secret_storage": False,
        },
        "summary": {
            "targets": len(public_targets),
            "runnable_openai_compatible_targets": sum(1 for target in targets if target.runnable_openai_compatible()),
            "interesting_env_values": len(values),
            "config_files_found": len(file_results),
            "codex_route_type": client_route_type(assessment, "codex"),
            "claude_code_route_type": client_route_type(assessment, "claude_code"),
            "local_switcher_status": assessment["local_switcher"]["status"],
        },
        "assessment": assessment,
        "targets": public_targets,
        "values": [asdict(item) for item in values],
        "files": file_results,
    }
    return report


def client_route_type(assessment: dict[str, Any], client: str) -> str:
    for item in assessment.get("clients", []):
        if item.get("client") == client:
            return str(item.get("route_type", "unknown"))
    return "unknown"


def assess_local_routes(
    targets: list[LocalTarget],
    file_results: list[dict[str, Any]],
    probe_local: bool = True,
) -> dict[str, Any]:
    clients = [
        assess_client_route("codex", targets, file_results),
        assess_client_route("claude_code", targets, file_results),
    ]
    local_urls = sorted({target.base_url for target in targets if target.base_url and is_loopback_url(target.base_url)})
    switcher_sources = sorted(
        {
            source
            for source in [target.source for target in targets] + [item["path"] for item in file_results]
            if looks_like_switcher_source(source)
        }
    )
    probes = [probe_local_base_url(url) for url in local_urls] if probe_local else [not_probed_local_url(url) for url in local_urls]
    reachable = any(item.get("reachable") for item in probes)
    if reachable:
        status = "reachable"
    elif local_urls and probe_local:
        status = "configured_but_unreachable"
    elif local_urls:
        status = "configured_not_probed"
    elif switcher_sources:
        status = "config_detected_no_local_url"
    else:
        status = "not_detected"

    return {
        "clients": clients,
        "local_switcher": {
            "status": status,
            "probe_localhost_only": True,
            "configured_local_base_urls": [redact_urlish(url) for url in local_urls],
            "configured_sources": switcher_sources,
            "probes": probes,
            "notes": [
                "Local switcher probing only touches loopback/localhost URLs and sends no API key.",
                "A reachable local API does not prove Codex or Claude Code is using it unless their detected base URL points to it.",
            ],
        },
    }


def assess_client_route(client: str, targets: list[LocalTarget], file_results: list[dict[str, Any]]) -> dict[str, Any]:
    related = [target for target in targets if target_matches_client(target, client)]
    selected = first_preferred_target(related)
    auth_files = auth_files_for_client(file_results, client)
    evidence: list[str] = []
    for target in related[:5]:
        label = target.name
        if target.base_url:
            evidence.append(f"{label} base_url={redact_urlish(target.base_url)}")
        if target.model:
            evidence.append(f"{label} model={target.model}")
        if target.api_key or target.api_key_name:
            evidence.append(f"{label} key_present name={target.api_key_name or 'unknown'}")
    for path in auth_files[:3]:
        evidence.append(f"auth_file_present={path}")

    base_url = selected.base_url if selected else None
    model = selected.model if selected else None
    host_kind = classify_endpoint_host(base_url, selected.protocol if selected else None)
    has_env_or_file_key = any(target.api_key or target.api_key_name for target in related)
    has_auth_file = bool(auth_files)

    route_type = "unknown"
    confidence = "low"
    auth_mode = "unknown"
    notes: list[str] = []

    if host_kind == "local_loopback":
        route_type = "local_switcher_or_proxy"
        confidence = "high"
        auth_mode = "api_key_or_token_via_local_proxy" if has_env_or_file_key else "local_proxy_without_detected_key"
    elif host_kind == "third_party":
        route_type = "third_party_api"
        confidence = "high"
        auth_mode = "api_key_or_token" if has_env_or_file_key else "custom_endpoint_without_detected_key"
    elif host_kind == "official_cloud":
        route_type = "official_cloud_api"
        confidence = "high" if has_env_or_file_key else "medium"
        auth_mode = "api_key" if has_env_or_file_key else "unknown"
    elif host_kind == "official_provider":
        if has_env_or_file_key:
            route_type = "official_api_key"
            confidence = "high"
            auth_mode = "api_key_or_token"
        elif has_auth_file:
            route_type = "official_account_login_likely"
            confidence = "medium"
            auth_mode = "account_login_or_oauth_file"
        else:
            route_type = "official_endpoint_configured"
            confidence = "low"
            auth_mode = "unknown"
    elif has_auth_file and not base_url:
        route_type = "official_account_login_likely"
        confidence = "medium"
        auth_mode = "account_login_or_oauth_file"
    elif has_env_or_file_key and not base_url:
        route_type = "official_api_key_default_endpoint_likely"
        confidence = "medium"
        auth_mode = "api_key_or_token"
    elif related:
        notes.append("Detected related config, but not enough evidence to classify the endpoint route.")

    if selected and looks_like_switcher_source(selected.source + " " + selected.name + " " + selected.provider_hint):
        notes.append("Config source looks like a local switcher/router profile; verify the selected profile before treating it as the active client route.")
    if not related and not has_auth_file:
        notes.append("No related environment variables or known auth/config files were detected.")

    return {
        "client": client,
        "route_type": route_type,
        "confidence": confidence,
        "auth_mode": auth_mode,
        "base_url": redact_urlish(base_url),
        "model": model,
        "evidence": evidence,
        "notes": notes,
    }


def first_preferred_target(targets: list[LocalTarget]) -> LocalTarget | None:
    if not targets:
        return None
    env_targets = [target for target in targets if target.source == "environment"]
    with_base = [target for target in env_targets if target.base_url]
    if with_base:
        return with_base[0]
    if env_targets:
        return env_targets[0]
    with_base = [target for target in targets if target.base_url]
    return with_base[0] if with_base else targets[0]


def target_matches_client(target: LocalTarget, client: str) -> bool:
    text = f"{target.name} {target.provider_hint} {target.source} {target.protocol}".lower()
    if client == "codex":
        return "codex" in text or "openai" in text or target.protocol in {"openai-compatible", "azure-openai"}
    if client == "claude_code":
        return "claude" in text or "anthropic" in text or "ccswitch" in text or "claude-code-router" in text
    return False


def auth_files_for_client(file_results: list[dict[str, Any]], client: str) -> list[str]:
    paths: list[str] = []
    for item in file_results:
        path = str(item.get("path", ""))
        lower = path.lower().replace("\\", "/")
        values = item.get("values", [])
        has_secret = any(value.get("value_kind") == "secret" and value.get("present") for value in values)
        if client == "codex" and "/.codex/auth" in lower:
            paths.append(path)
        elif client == "claude_code" and ("/.claude/.credentials" in lower or ("claude" in lower and has_secret)):
            paths.append(path)
    return paths


def classify_endpoint_host(base_url: str | None, protocol: str | None = None) -> str:
    if not base_url:
        return "default_or_missing"
    host = hostname_of(base_url)
    if not host:
        return "unknown"
    if is_loopback_host(host):
        return "local_loopback"
    if protocol == "azure-openai" or host.endswith(".openai.azure.com") or host.endswith(".services.ai.azure.com"):
        return "official_cloud"
    if host in OPENAI_OFFICIAL_HOSTS or host.endswith(".openai.com"):
        return "official_provider"
    if host in ANTHROPIC_OFFICIAL_HOSTS or host.endswith(".anthropic.com"):
        return "official_provider"
    return "third_party"


def hostname_of(url: str | None) -> str | None:
    if not url or "://" not in url:
        return None
    try:
        return (urlsplit(url).hostname or "").lower() or None
    except Exception:
        return None


def is_loopback_url(url: str | None) -> bool:
    host = hostname_of(url)
    return bool(host and is_loopback_host(host))


def is_loopback_host(host: str) -> bool:
    normalized = host.strip("[]").lower()
    if normalized in {"localhost", "localhost.localdomain"} or normalized.endswith(".localhost"):
        return True
    try:
        return ip_address(normalized).is_loopback
    except ValueError:
        return False


def looks_like_switcher_source(source: str) -> bool:
    lower = source.lower()
    return "ccswitch" in lower or "cc-switch" in lower or "claude-code-router" in lower


def not_probed_local_url(url: str) -> dict[str, Any]:
    return {
        "base_url": redact_urlish(url),
        "reachable": None,
        "attempted": False,
        "reason": "local probing disabled",
    }


def probe_local_base_url(url: str) -> dict[str, Any]:
    candidates = local_probe_candidates(url)
    attempts: list[dict[str, Any]] = []
    for candidate in candidates:
        result = probe_single_local_url(candidate)
        attempts.append(result)
        if result.get("reachable"):
            return {
                "base_url": redact_urlish(url),
                "reachable": True,
                "attempted": True,
                "winning_url": result["url"],
                "status_code": result.get("status_code"),
                "attempts": attempts,
            }
    return {
        "base_url": redact_urlish(url),
        "reachable": False,
        "attempted": True,
        "attempts": attempts,
    }


def local_probe_candidates(url: str) -> list[str]:
    try:
        parts = urlsplit(url)
    except Exception:
        return []
    host = parts.hostname or ""
    if not host or not is_loopback_host(host):
        return []
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if parts.port:
        host = f"{host}:{parts.port}"
    root = urlunsplit((parts.scheme, host, "", "", ""))
    base_path = parts.path.rstrip("/")
    base = urlunsplit((parts.scheme, host, base_path, "", "")) if base_path else root
    candidates = [base, root + "/health", root + "/api/health", root + "/v1/models"]
    if base_path and not base_path.endswith("/v1"):
        candidates.append(base + "/v1/models")
    elif base_path.endswith("/v1"):
        candidates.append(base + "/models")
    unique: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            unique.append(candidate)
    return unique


def probe_single_local_url(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": "relayprobe-local-detector/0.1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=1.0) as response:
            return {"url": redact_urlish(url), "reachable": True, "status_code": response.getcode()}
    except urllib.error.HTTPError as exc:
        return {"url": redact_urlish(url), "reachable": True, "status_code": exc.code}
    except Exception as exc:
        return {"url": redact_urlish(url), "reachable": False, "error": exc.__class__.__name__}

def detect_targets_raw(
    env: dict[str, str] | None = None,
    home: Path | None = None,
    appdata: Path | None = None,
    include_file_secrets: bool = False,
) -> list[LocalTarget]:
    env = dict(os.environ if env is None else env)
    home = Path.home() if home is None else home
    appdata = Path(env.get("APPDATA", "")) if appdata is None and env.get("APPDATA") else appdata
    report_targets: list[LocalTarget] = []
    for provider, spec in ENV_CANDIDATES.items():
        api_key_name, api_key = first_env(env, spec["api_key"])
        _, base_url = first_env(env, spec["base_url"])
        _, model = first_env(env, spec["model"])
        if api_key or base_url or model:
            report_targets.append(
                LocalTarget(
                    name=provider,
                    provider_hint=provider,
                    protocol=spec["protocol"],
                    source="environment",
                    api_key=api_key,
                    api_key_name=api_key_name,
                    base_url=base_url,
                    model=model,
                )
            )
    if include_file_secrets:
        report_targets.extend(detect_file_targets_raw(env=env, home=home, appdata=appdata))
    return report_targets


def detect_file_targets_raw(env: dict[str, str], home: Path, appdata: Path | None) -> list[LocalTarget]:
    targets: list[LocalTarget] = []
    for path in candidate_paths(home, appdata, env):
        if not path.exists() or not path.is_file():
            continue
        values = extract_file_values_raw(path)
        targets.extend(targets_from_file_raw(path, values))
    targets.extend(combine_file_targets_for_live_run(targets))
    return targets


def combine_file_targets_for_live_run(targets: list[LocalTarget]) -> list[LocalTarget]:
    combined: list[LocalTarget] = []
    for provider_hint, protocol in (("codex", "openai-compatible"), ("claude-code", "anthropic-messages")):
        related = [target for target in targets if target.provider_hint == provider_hint]
        if not related:
            continue
        base = next((target.base_url for target in related if target.base_url), None)
        model = next((target.model for target in related if target.model), None)
        key_target = next((target for target in related if target.api_key), None)
        if base and key_target:
            combined.append(
                LocalTarget(
                    name="combined-local:" + provider_hint,
                    provider_hint=provider_hint,
                    protocol=protocol,
                    source="combined local config files",
                    api_key=key_target.api_key,
                    api_key_name=key_target.api_key_name,
                    base_url=base,
                    model=model,
                    notes=[
                        "explicit opt-in live run target assembled from local config files",
                        "raw key is held in memory only and is not written to reports",
                    ],
                )
            )
    return combined


def first_env(env: dict[str, str], names: list[str]) -> tuple[str | None, str | None]:
    for name in names:
        if name in env and env[name]:
            return name, env[name]
    return None, None


def is_interesting_key(key: str) -> bool:
    return bool(SECRET_KEY_RE.search(key) or BASE_URL_RE.search(key) or MODEL_RE.search(key))


def classify_key(key: str) -> str:
    if SECRET_KEY_RE.search(key):
        return "secret"
    if BASE_URL_RE.search(key):
        return "base_url"
    if MODEL_RE.search(key):
        return "model"
    return "other"


def candidate_paths(home: Path, appdata: Path | None, env: dict[str, str] | None = None) -> list[Path]:
    paths = [home / rel for rel in FILE_CANDIDATES]
    if appdata:
        paths.extend(
            [
                appdata / "Claude" / "claude_desktop_config.json",
                appdata / "Codex" / "config.json",
                appdata / "ccswitch" / "config.json",
            ]
        )
    env = env or {}
    for name in ("CODEX_HOME", "CODEX_CONFIG_DIR"):
        if env.get(name):
            root = Path(env[name])
            paths.extend([root / "config.toml", root / "config.json", root / "auth.json"])
    for name in ("CLAUDE_CONFIG_DIR", "CLAUDE_CODE_CONFIG_DIR"):
        if env.get(name):
            root = Path(env[name])
            paths.extend([root / "config.json", root / "settings.json", root / "settings.local.json", root / ".credentials.json"])
    for name in ("CCSWITCH_HOME", "CCSWITCH_CONFIG_DIR"):
        if env.get(name):
            root = Path(env[name])
            paths.extend([root / "config.json", root / "settings.json"])

    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def extract_file_values(path: Path) -> list[LocalValue]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return [
            LocalValue(
                name="read_error",
                value_kind="error",
                value_redacted=str(exc),
                present=True,
                source_type="file",
                source=str(path),
            )
        ]

    parsed: Any | None = None
    if path.suffix.lower() == ".json":
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = None
    if parsed is None:
        parsed = parse_key_value_text(text)

    found: list[LocalValue] = []
    for key, value in walk_values(parsed):
        if not is_interesting_key(key):
            continue
        value_str = "" if value is None else str(value)
        kind = classify_key(key)
        found.append(
            LocalValue(
                name=key,
                value_kind=kind,
                value_redacted=redact_value(kind, value_str),
                present=value_str != "",
                source_type="file",
                source=str(path),
                fingerprint8=fingerprint8(value_str) if kind == "secret" and value_str else None,
            )
        )
    return found


def extract_file_values_raw(path: Path) -> list[dict[str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    parsed: Any | None = None
    if path.suffix.lower() == ".json":
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = None
    if parsed is None:
        parsed = parse_key_value_text(text)

    values: list[dict[str, str]] = []
    for key, value in walk_values(parsed):
        if not is_interesting_key(key):
            continue
        value_str = "" if value is None else str(value)
        if not value_str:
            continue
        values.append({"name": key, "value_kind": classify_key(key), "value": value_str})
    return values


def targets_from_file_raw(path: Path, values: list[dict[str, str]]) -> list[LocalTarget]:
    base_urls = [item for item in values if item["value_kind"] == "base_url"]
    models = [item for item in values if item["value_kind"] == "model"]
    secrets = sorted((item for item in values if item["value_kind"] == "secret"), key=secret_priority)
    if not (base_urls or models or secrets):
        return []
    provider_hint = provider_hint_for_path(path)
    protocol = protocol_for_provider_hint(provider_hint)
    first_secret = secrets[0] if secrets else None
    return [
        LocalTarget(
            name="config-file-raw:" + path.name,
            provider_hint=provider_hint,
            protocol=protocol,
            source=str(path),
            api_key=first_secret["value"] if first_secret else None,
            api_key_name=first_secret["name"] if first_secret else None,
            base_url=base_urls[0]["value"] if base_urls else None,
            model=models[0]["value"] if models else None,
            notes=[
                "raw secret available only for explicit opt-in live run",
                "raw key is held in memory only and is not written to reports",
            ],
        )
    ]


def secret_priority(item: dict[str, str]) -> tuple[int, str]:
    name = item["name"].lower().replace("-", "_")
    if "refresh" in name:
        return (90, name)
    if "api_key" in name or ("api" in name and "key" in name):
        return (0, name)
    if "bearer" in name:
        return (1, name)
    if "auth_token" in name or "access_token" in name:
        return (2, name)
    if "token" in name:
        return (10, name)
    return (50, name)


def parse_key_value_text(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)\s*[:=]\s*(.+)$", stripped)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip().strip('"').strip("'")
        result[key] = value
    return result


def walk_values(data: Any, prefix: str = "") -> list[tuple[str, Any]]:
    values: list[tuple[str, Any]] = []
    if isinstance(data, dict):
        for key, value in data.items():
            full = f"{prefix}.{key}" if prefix else str(key)
            values.extend(walk_values(value, full))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            full = f"{prefix}.{index}" if prefix else str(index)
            values.extend(walk_values(value, full))
    else:
        values.append((prefix, data))
    return values


def targets_from_file(path: Path, extracted: list[LocalValue]) -> list[LocalTarget]:
    base_urls = [item for item in extracted if item.value_kind == "base_url" and item.value_redacted]
    models = [item for item in extracted if item.value_kind == "model" and item.value_redacted]
    secrets = [item for item in extracted if item.value_kind == "secret" and item.present]
    if not (base_urls or models or secrets):
        return []
    provider_hint = provider_hint_for_path(path)
    protocol = protocol_for_provider_hint(provider_hint)
    return [
        LocalTarget(
            name="config-file:" + path.name,
            provider_hint=provider_hint,
            protocol=protocol,
            source=str(path),
            api_key=None,
            api_key_name=secrets[0].name if secrets else None,
            base_url=base_urls[0].value_redacted if base_urls else None,
            model=models[0].value_redacted if models else None,
            notes=["file secrets are redacted and not used for automatic network runs"],
        )
    ]


def provider_hint_for_path(path: Path) -> str:
    lower = str(path).lower().replace("\\", "/")
    if "/.codex/" in lower or "/codex/" in lower:
        return "codex"
    if "claude-code-router" in lower:
        return "claude-code-router"
    if "/.claude" in lower or "/claude/" in lower or "claude-code" in lower:
        return "claude-code"
    if "ccswitch" in lower or "cc-switch" in lower:
        return "ccswitch"
    return "config-file"


def protocol_for_provider_hint(provider_hint: str) -> str:
    if provider_hint == "codex":
        return "openai-compatible"
    if provider_hint in {"claude-code", "claude-code-router"}:
        return "anthropic-messages"
    return "unknown"
