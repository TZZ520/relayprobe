from __future__ import annotations

import unittest

from relayprobe.analyzers import content
from relayprobe.runner import Runner
from relayprobe.schemas import Target
from relayprobe.transport import MockTransport


class AnalyzerTests(unittest.TestCase):
    def run_mock(self, mode: str):
        target = Target(name="mock", base_url="mock://relayprobe", model="gpt-4o")
        return Runner(target, MockTransport(mode)).run_core()

    def test_clean_mock_has_no_suspect_or_fail(self) -> None:
        report = self.run_mock("clean")
        self.assertEqual(report["summary"]["fail"], 0)
        self.assertEqual(report["summary"]["suspect"], 0)
        self.assertGreaterEqual(report["summary"]["pass"], 8)

    def test_tampered_mock_detects_multiple_suspects(self) -> None:
        report = self.run_mock("tampered")
        self.assertEqual(report["summary"]["fail"], 0)
        self.assertGreaterEqual(report["summary"]["suspect"], 7)

    def test_content_extraction(self) -> None:
        class Record:
            response_json = {"choices": [{"message": {"content": "hello"}}]}

        self.assertEqual(content(Record()), "hello")


if __name__ == "__main__":
    unittest.main()

