"""Tests for PACT Slack progress formatter/watcher."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parent

spec = importlib.util.spec_from_file_location(
    "pact_format_event",
    str(SCRIPTS / "pact_format_event.py"),
)
assert spec is not None and spec.loader is not None
fmt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fmt)


class TestPactFormatEvent(unittest.TestCase):
    def test_loop_done_minimal_clean_block(self):
        event = {
            "event": "loop_done",
            "round": 3,
            "head": "c092ca917c7a7ce098a1c822debe0c90e474077e",
            "p0": 0,
            "p1": 0,
            "p2": 0,
            "p3": 0,
            "commentUrl": "https://github.com/fastxyz/fast-shop/pull/443#issuecomment-4579997361",
            "summary": "This clean summary should not be printed.",
        }
        out = fmt.format_event("fastxyz/fast-shop", "443", "Codex", "loop", event)
        self.assertIn("**PACT <https://github.com/fastxyz/fast-shop/pull/443|#443>** Codex loop Round **R3 / CLEAN**", out)
        self.assertIn("[<https://github.com/fastxyz/fast-shop/pull/443#issuecomment-4579997361|LOOP_DONE comment>]", out)
        self.assertIn("**P0/P1/P2/P3 = 0/0/0/0**", out)
        self.assertIn("Reviewed commit: <https://github.com/fastxyz/fast-shop/commit/c092ca917c7a7ce098a1c822debe0c90e474077e|c092ca91>", out)
        self.assertNotIn("This clean summary", out)

    def test_findings_include_summary_and_clickable_line(self):
        event = {
            "event": "round",
            "round": 2,
            "head": "ad29edbc7668606ddf8a43bf9651445af0a62691",
            "p0": 0,
            "p1": 0,
            "p2": 1,
            "p3": 0,
            "summary": "Found one blocking address-change pending card product snapshot gap after the first fix.",
            "findings": [
                {
                    "severity": "P2",
                    "lane": "SP",
                    "loc": "apps/api/public/assets/chat-widget.js:5059-5072",
                    "issue": "Address-change quote_pending reuses an existing Quote card DOM.",
                }
            ],
        }
        out = fmt.format_event("fastxyz/fast-shop", "443", "Codex", "loop", event)
        self.assertIn("**P0/P1/P2/P3 = 0/0/1/0**", out)
        self.assertIn("Found one blocking address-change", out)
        self.assertIn("• **P2**: [SP]", out)
        self.assertIn("<https://github.com/fastxyz/fast-shop/blob/ad29edbc7668606ddf8a43bf9651445af0a62691/apps/api/public/assets/chat-widget.js#L5059-L5072|apps/api/public/assets/chat-widget.js:5059-5072>", out)

    def test_review_clean_minimal_block(self):
        event = {
            "event": "review_clean",
            "head": "c092ca917c7a7ce098a1c822debe0c90e474077e",
            "p0": 0,
            "p1": 0,
            "p2": 0,
            "p3": 0,
            "commentUrl": "https://github.com/fastxyz/fast-shop/pull/443#issuecomment-4580040524",
            "summary": "Clean summary should not be printed.",
        }
        out = fmt.format_event("fastxyz/fast-shop", "443", "Claude", "review", event)
        self.assertEqual(
            out,
            "**PACT <https://github.com/fastxyz/fast-shop/pull/443|#443>** Claude review **CLEAN** [<https://github.com/fastxyz/fast-shop/pull/443#issuecomment-4580040524|REVIEW_CLEAN comment>]\n"
            "**P0/P1/P2/P3 = 0/0/0/0**\n"
            "Reviewed commit: <https://github.com/fastxyz/fast-shop/commit/c092ca917c7a7ce098a1c822debe0c90e474077e|c092ca91>",
        )


class TestPactProgressWatch(unittest.TestCase):
    def test_clean_round_and_loop_done_are_merged(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            progress = run_dir / "progress.jsonl"
            progress.write_text(
                json.dumps({"event": "started"})
                + "\n"
                + json.dumps(
                    {
                        "event": "round",
                        "round": 3,
                        "head": "c092ca917c7a7ce098a1c822debe0c90e474077e",
                        "p0": 0,
                        "p1": 0,
                        "p2": 0,
                        "p3": 0,
                        "summary": "Clean round should be held for loop_done.",
                    }
                )
                + "\n"
                + json.dumps(
                    {
                        "event": "loop_done",
                        "round": 3,
                        "head": "c092ca917c7a7ce098a1c822debe0c90e474077e",
                        "p0": 0,
                        "p1": 0,
                        "p2": 0,
                        "p3": 0,
                        "commentUrl": "https://github.com/fastxyz/fast-shop/pull/443#issuecomment-4579997361",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "pact_progress_watch.py"),
                    "--run-dir",
                    str(run_dir),
                    "--repo",
                    "fastxyz/fast-shop",
                    "--pr",
                    "443",
                    "--vendor",
                    "codex-cli",
                    "--vendor-label",
                    "Codex",
                    "--mode",
                    "loop",
                    "--state",
                    str(run_dir / "state.json"),
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertEqual(proc.stdout.count("Codex loop Round"), 1)
            self.assertIn("Round **R3 / CLEAN**", proc.stdout)
            self.assertNotIn("Clean round should be held", proc.stdout)


if __name__ == "__main__":
    unittest.main()
