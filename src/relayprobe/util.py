from __future__ import annotations

import hashlib
import json
import re
import uuid
from typing import Any


def nonce(prefix: str = "rp") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def request_hash(body: dict[str, Any]) -> str:
    return sha256_text(canonical_json(body))


def chat_content(messages: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for message in messages:
        content = message.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
    return "\n".join(parts)


def extract_tag(text: str, tag: str) -> str | None:
    match = re.search(rf"{re.escape(tag)}:([A-Za-z0-9_\-]+)", text)
    if not match:
        return None
    return match.group(1)


def safe_json_loads(text: str) -> Any | None:
    try:
        return json.loads(text)
    except Exception:
        return None

