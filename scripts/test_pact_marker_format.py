"""Tests for deterministic PACT marker formatter."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parent
FORMATTER = SCRIPTS / "pact_format_marker.py"
VALIDATOR = SCRIPTS / "validate-marker.py"


def run_formatter(payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(FORMATTER), "--marker-json", json.dumps(payload)],
        text=True,
        capture_output=True,
        check=False,
    )


def validate_marker(text: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR)],
        input=text,
        text=True,
        capture_output=True,
        check=False,
    )


class TestPactMarkerFormatter(unittest.TestCase):
    def test_loop_done_marker_is_schema_valid_and_never_uses_pass_shorthand(self):
        payload = {
            "kind": "LOOP_DONE",
            "vendor": "codex-cli",
            "head": "c092ca917c7a7ce098a1c822debe0c90e474077e",
            "internal_rounds": 3,
            "lanes": {
                "CQ": {"p0": 0, "p1": 0, "p2": 0, "p3": 0, "nit": 0},
                "SP": {"p0": 0, "p1": 0, "p2": 0, "p3": 0, "nit": 0},
                "TC": {"p0": 0, "p1": 0, "p2": 0, "p3": 0, "nit": 0},
            },
            "gates": [
                {"name": "test", "status": "PASS", "detail": "npm test"},
                {"name": "build", "status": "PASS", "detail": "npm run build"},
            ],
            "ci": "green",
            "commits": ["ad29edb", "c092ca9"],
        }

        proc = run_formatter(payload)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        marker = proc.stdout
        self.assertIn(
            "LOOP_DONE_codex-cli_c092ca917c7a7ce098a1c822debe0c90e474077e "
            "TOTAL P0=0 P1=0 P2=0 P3=0 | "
            "CQ P0=0 P1=0 P2=0 P3=0 | "
            "SP P0=0 P1=0 P2=0 P3=0 | "
            "TC P0=0 P1=0 P2=0 P3=0",
            marker,
        )
        self.assertIn("Internal rounds taken: 3", marker)
        self.assertIn("  CQ: P0=0 P1=0 P2=0 P3=0 Nit=0", marker)
        self.assertNotIn("CQ PASS", marker)
        self.assertEqual(validate_marker(marker).returncode, 0, validate_marker(marker).stderr)

    def test_review_clean_marker_includes_existing_markers_and_validates(self):
        payload = {
            "kind": "REVIEW_CLEAN",
            "vendor": "claude-code",
            "head": "c092ca917c7a7ce098a1c822debe0c90e474077e",
            "existing_markers": [
                {
                    "title": "LOOP_DONE_codex-cli_c092ca917c7a7ce098a1c822debe0c90e474077e",
                    "posted": "2026-05-29T21:24:59Z",
                }
            ],
            "lanes": {
                "CQ": {"p0": 0, "p1": 0, "p2": 0, "p3": 0, "nit": 0},
                "SP": {"p0": 0, "p1": 0, "p2": 0, "p3": 0, "nit": 0},
                "TC": {"p0": 0, "p1": 0, "p2": 0, "p3": 0, "nit": 0},
            },
            "local_gates": "GitHub checks green",
            "ci_status": "green",
        }

        proc = run_formatter(payload)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        marker = proc.stdout
        self.assertIn("REVIEW_CLEAN_claude-code_c092ca917c7a7ce098a1c822debe0c90e474077e TOTAL", marker)
        self.assertIn("HEAD reviewed: c092ca917c7a7ce098a1c822debe0c90e474077e", marker)
        self.assertIn("Existing markers on HEAD:", marker)
        self.assertIn("  - LOOP_DONE_codex-cli_c092ca917c7a7ce098a1c822debe0c90e474077e  (posted 2026-05-29T21:24:59Z)", marker)
        self.assertNotIn("TC PASS", marker)
        self.assertEqual(validate_marker(marker).returncode, 0, validate_marker(marker).stderr)

    def test_review_findings_can_compute_lane_counts_from_findings(self):
        payload = {
            "kind": "REVIEW_FINDINGS",
            "vendor": "claude-code",
            "round": 2,
            "head": "b8e1d44e123456789abcdef1234567890abcdef1",
            "existing_markers": "none",
            "findings": [
                {"lane": "SP", "severity": "P1", "loc": "src/auth/refresh.ts:88", "summary": "old token remains valid"},
                {"lane": "TC", "severity": "P2", "loc": "tests/auth/refresh.test.ts:1", "summary": "missing race test"},
                {"lane": "CQ", "severity": "P3", "loc": "src/auth/refresh.ts:42", "summary": "extract helper"},
            ],
            "local_gates": "typecheck=PASS, lint=PASS, test=PASS",
            "ci_status": "green",
        }

        proc = run_formatter(payload)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        marker = proc.stdout
        self.assertIn(
            "REVIEW_FINDINGS_claude-code_R2_b8e1d44e123456789abcdef1234567890abcdef1 "
            "TOTAL P0=0 P1=1 P2=1 P3=1 | "
            "CQ P0=0 P1=0 P2=0 P3=1 | "
            "SP P0=0 P1=1 P2=0 P3=0 | "
            "TC P0=0 P1=0 P2=1 P3=0",
            marker,
        )
        self.assertIn("  - [SP P1 #1] src/auth/refresh.ts:88 — old token remains valid", marker)
        self.assertEqual(validate_marker(marker).returncode, 0, validate_marker(marker).stderr)

    def test_clean_markers_reject_blocking_counts_before_posting(self):
        payload = {
            "kind": "REVIEW_CLEAN",
            "vendor": "claude-code",
            "head": "abc1234d567890abcdef1234567890abcdef1234",
            "existing_markers": "none",
            "lanes": {
                "CQ": {"p0": 0, "p1": 0, "p2": 1, "p3": 0, "nit": 0},
                "SP": {"p0": 0, "p1": 0, "p2": 0, "p3": 0, "nit": 0},
                "TC": {"p0": 0, "p1": 0, "p2": 0, "p3": 0, "nit": 0},
            },
        }

        proc = run_formatter(payload)

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("REVIEW_CLEAN cannot contain P0/P1/P2 findings", proc.stderr)


if __name__ == "__main__":
    unittest.main()
