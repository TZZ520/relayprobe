from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from relayprobe.local_config import detect_local_config, detect_targets_raw, local_probe_candidates, redact_secret, redact_urlish


class LocalConfigTests(unittest.TestCase):
    def test_redacts_secret_and_url_credentials(self) -> None:
        self.assertEqual(redact_secret("sk-abcdefgh12345678"), "sk-a...5678")
        self.assertEqual(redact_secret("short"), "***")
        self.assertEqual(
            redact_urlish("https://user:pass@relay.example.com/v1?api_key=sk-secret&model=gpt-4o"),
            "https://***:***@relay.example.com/v1?api_key=***&model=gpt-4o",
        )

    def test_env_detection_keeps_raw_key_out_of_public_report(self) -> None:
        secret = "sk-test-abcdefghijklmnop"
        env = {
            "OPENAI_API_KEY": secret,
            "OPENAI_BASE_URL": "https://relay.example.com/v1",
            "OPENAI_MODEL": "gpt-4o",
        }
        with tempfile.TemporaryDirectory() as tmp:
            report = detect_local_config(env=env, home=Path(tmp), appdata=None)

        self.assertEqual(report["summary"]["targets"], 1)
        self.assertEqual(report["summary"]["runnable_openai_compatible_targets"], 1)
        target = report["targets"][0]
        self.assertEqual(target["name"], "codex/openai-compatible")
        self.assertTrue(target["api_key_present"])
        self.assertEqual(target["api_key_redacted"], "sk-t...mnop")
        self.assertEqual(target["base_url"], "https://relay.example.com/v1")
        self.assertEqual(target["model"], "gpt-4o")
        self.assertNotIn(secret, json.dumps(report, ensure_ascii=False))

        raw_targets = detect_targets_raw(env=env)
        self.assertEqual(raw_targets[0].api_key, secret)

    def test_file_detection_is_redacted_and_not_runnable(self) -> None:
        secret = "sk-file-abcdefghijklmnop"
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config = home / ".codex" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        'model = "gpt-4o"',
                        'base_url = "https://relay.example.com/v1?token=hidden"',
                        f'api_key = "{secret}"',
                    ]
                ),
                encoding="utf-8",
            )
            report = detect_local_config(env={}, home=home, appdata=None)

        self.assertEqual(report["summary"]["config_files_found"], 1)
        self.assertEqual(report["summary"]["runnable_openai_compatible_targets"], 0)
        self.assertNotIn(secret, json.dumps(report, ensure_ascii=False))
        self.assertIn("token=***", json.dumps(report, ensure_ascii=False))
        file_target = report["targets"][0]
        self.assertFalse(file_target["api_key_present"])
        self.assertEqual(file_target["api_key_name"], "api_key")
        self.assertIn("file secrets are redacted", file_target["notes"][0])

    def test_file_secret_is_raw_only_for_explicit_live_opt_in(self) -> None:
        secret = "sk-live-abcdefghijklmnop"
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config = home / ".codex" / "config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                '\n'.join(
                    [
                        'model = "gpt-4o"',
                        'base_url = "https://relay.example.com/v1"',
                        f'experimental_bearer_token = "{secret}"',
                    ]
                ),
                encoding="utf-8",
            )
            public_report = detect_local_config(env={}, home=home, appdata=None, probe_local=False)
            raw_targets_default = detect_targets_raw(env={}, home=home, appdata=None)
            raw_targets_opt_in = detect_targets_raw(env={}, home=home, appdata=None, include_file_secrets=True)

        self.assertNotIn(secret, json.dumps(public_report, ensure_ascii=False))
        self.assertFalse(raw_targets_default)
        runnable = [target for target in raw_targets_opt_in if target.runnable_openai_compatible()]
        self.assertEqual(runnable[0].api_key, secret)
        self.assertEqual(runnable[0].base_url, "https://relay.example.com/v1")

    def test_claude_auth_token_env_is_detected(self) -> None:
        env = {
            "ANTHROPIC_AUTH_TOKEN": "anthropic-token-abcdefghijklmnop",
            "ANTHROPIC_BASE_URL": "https://claude-relay.example.com",
            "ANTHROPIC_MODEL": "claude-sonnet-4",
        }
        with tempfile.TemporaryDirectory() as tmp:
            report = detect_local_config(env=env, home=Path(tmp), appdata=None)

        self.assertEqual(report["targets"][0]["protocol"], "anthropic-messages")
        self.assertFalse(report["targets"][0]["runnable_openai_compatible"])
        self.assertNotIn("anthropic-token-abcdefghijklmnop", json.dumps(report, ensure_ascii=False))
        self.assertEqual(report["summary"]["claude_code_route_type"], "third_party_api")

    def test_route_assessment_distinguishes_third_party_and_local_switcher(self) -> None:
        env = {
            "OPENAI_API_KEY": "sk-test-abcdefghijklmnop",
            "OPENAI_BASE_URL": "https://relay.thirdparty.example/v1",
            "OPENAI_MODEL": "gpt-4o",
            "ANTHROPIC_AUTH_TOKEN": "anthropic-token-abcdefghijklmnop",
            "ANTHROPIC_BASE_URL": "http://127.0.0.1:3456",
            "ANTHROPIC_MODEL": "claude-sonnet-4",
        }
        with tempfile.TemporaryDirectory() as tmp:
            report = detect_local_config(env=env, home=Path(tmp), appdata=None, probe_local=False)

        self.assertEqual(report["summary"]["codex_route_type"], "third_party_api")
        self.assertEqual(report["summary"]["claude_code_route_type"], "local_switcher_or_proxy")
        self.assertEqual(report["summary"]["local_switcher_status"], "configured_not_probed")
        self.assertEqual(report["assessment"]["local_switcher"]["configured_local_base_urls"], ["http://127.0.0.1:3456"])

    def test_codex_auth_file_is_classified_as_official_account_login_likely(self) -> None:
        secret = "codex-access-token-abcdefghijklmnop"
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            auth = home / ".codex" / "auth.json"
            auth.parent.mkdir(parents=True)
            auth.write_text(json.dumps({"tokens": {"access_token": secret}}), encoding="utf-8")
            report = detect_local_config(env={}, home=home, appdata=None, probe_local=False)

        self.assertEqual(report["summary"]["codex_route_type"], "official_account_login_likely")
        self.assertNotIn(secret, json.dumps(report, ensure_ascii=False))

    def test_codex_config_does_not_drive_claude_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            codex_config = home / ".codex" / "config.toml"
            claude_settings = home / ".claude" / "settings.json"
            codex_config.parent.mkdir(parents=True)
            claude_settings.parent.mkdir(parents=True)
            codex_config.write_text(
                '\n'.join(['base_url = "https://relay.thirdparty.example/v1"', 'model = "gpt-4o"']),
                encoding="utf-8",
            )
            claude_settings.write_text(
                json.dumps({"base_url": "http://127.0.0.1:3456", "model": "claude-sonnet-4"}),
                encoding="utf-8",
            )
            report = detect_local_config(env={}, home=home, appdata=None, probe_local=False)

        self.assertEqual(report["summary"]["codex_route_type"], "third_party_api")
        self.assertEqual(report["summary"]["claude_code_route_type"], "local_switcher_or_proxy")

    def test_local_probe_candidates_never_include_url_credentials_or_query(self) -> None:
        candidates = local_probe_candidates("http://user:pass@localhost:3456/v1?api_key=secret")
        self.assertIn("http://localhost:3456/v1", candidates)
        self.assertIn("http://localhost:3456/v1/models", candidates)
        self.assertTrue(all("secret" not in item and "user" not in item and "pass" not in item for item in candidates))


if __name__ == "__main__":
    unittest.main()
