from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from relayprobe.runner import Runner, write_report
from relayprobe.schemas import Target
from relayprobe.transport import MockTransport


class RunnerTests(unittest.TestCase):
    def test_report_write_and_summary(self) -> None:
        target = Target(name="mock", base_url="mock://relayprobe", model="gpt-4o")
        report = Runner(target, MockTransport("clean")).run_core()
        with tempfile.TemporaryDirectory() as tmp:
            json_path, markdown_path = write_report(report, tmp)
            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            loaded = json.loads(Path(json_path).read_text(encoding="utf-8"))
            self.assertEqual(loaded["summary"]["total"], 10)
            self.assertIn("request_integrity.echo_nonce", markdown_path.read_text(encoding="utf-8"))

    def test_bad_stream_is_suspect(self) -> None:
        target = Target(name="mock", base_url="mock://relayprobe", model="gpt-4o")
        report = Runner(target, MockTransport("bad_stream")).run_core()
        cases = {result["case_id"]: result for result in report["results"]}
        self.assertEqual(cases["stream.openai_sse"]["status"], "suspect")


if __name__ == "__main__":
    unittest.main()

