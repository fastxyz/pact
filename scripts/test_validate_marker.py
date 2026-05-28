"""Tests for validate-marker.py."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# pylint: disable=import-error,wrong-import-position
import importlib.util
spec = importlib.util.spec_from_file_location(
    "validate_marker",
    str(Path(__file__).parent / "validate-marker.py"),
)
vm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vm)


class TestCodeDone(unittest.TestCase):
    def test_minimal_valid(self):
        text = """CODE_DONE_codex-cli_abc1234

Vendor: codex-cli
HEAD: abc1234d567890abcdef1234567890abcdef1234
Responding to: initial implementation
Commits pushed: abc1234
Gates: typecheck=PASS, lint=PASS, test=PASS 100/100
CI: not yet fired
"""
        result = vm.validate_marker(text)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.kind, "CODE_DONE")
        self.assertEqual(result.vendor, "codex-cli")
        self.assertEqual(result.head_short, "abc1234")

    def test_missing_vendor_line(self):
        text = """CODE_DONE_codex-cli_abc1234

HEAD: abc1234d567890abcdef1234567890abcdef1234
Responding to: initial implementation
Commits pushed: abc1234
Gates: typecheck=PASS, lint=PASS, test=PASS 100/100
CI: not yet fired
"""
        result = vm.validate_marker(text)
        self.assertFalse(result.ok)
        self.assertIn("Vendor", " ".join(result.errors))


class TestReviewFindings(unittest.TestCase):
    def test_minimal_valid(self):
        text = """REVIEW_FINDINGS_claude-code_R1_b8e1d44 TOTAL P0=0 P1=1 P2=0 P3=0 | CQ P0=0 P1=1 P2=0 P3=0 | SP P0=0 P1=0 P2=0 P3=0 | TC P0=0 P1=0 P2=0 P3=0

Vendor: claude-code
Round: 1
HEAD reviewed: b8e1d44e123456789abcdef1234567890abcdef1
Existing markers on HEAD: none
Per-lane counts:
  CQ: P0=0 P1=1 P2=0 P3=0 Nit=0
  SP: P0=0 P1=0 P2=0 P3=0 Nit=0
  TC: P0=0 P1=0 P2=0 P3=0 Nit=0
Findings (each line-anchored):
  - [CQ P1 #1] src/foo.ts:42 — Inconsistent error handling
Local gates on this HEAD: typecheck=PASS, lint=PASS, test=PASS 100/100
CI status: green
"""
        result = vm.validate_marker(text)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.kind, "REVIEW_FINDINGS")
        self.assertEqual(result.round, 1)
        self.assertEqual(result.vendor, "claude-code")

    def test_review_marker_missing_first_line_counts_fails(self):
        text = """REVIEW_FINDINGS_claude-code_R1_b8e1d44

Vendor: claude-code
Round: 1
HEAD reviewed: b8e1d44e123456789abcdef1234567890abcdef1
Existing markers on HEAD: none
Per-lane counts:
  CQ: P0=0 P1=1 P2=0 P3=0 Nit=0
  SP: P0=0 P1=0 P2=0 P3=0 Nit=0
  TC: P0=0 P1=0 P2=0 P3=0 Nit=0
Findings (each line-anchored):
  - [CQ P1 #1] src/foo.ts:42 — Inconsistent error handling
Local gates on this HEAD: typecheck=PASS, lint=PASS, test=PASS 100/100
CI status: green
"""
        result = vm.validate_marker(text)
        self.assertFalse(result.ok)
        self.assertIn("aggregate and per-category P0/P1/P2/P3 counts", " ".join(result.errors))

    def test_review_marker_first_line_counts_must_match_lane_totals(self):
        text = """REVIEW_FINDINGS_claude-code_R1_b8e1d44 TOTAL P0=0 P1=0 P2=0 P3=0 | CQ P0=0 P1=0 P2=0 P3=0 | SP P0=0 P1=0 P2=0 P3=0 | TC P0=0 P1=0 P2=0 P3=0

Vendor: claude-code
Round: 1
HEAD reviewed: b8e1d44e123456789abcdef1234567890abcdef1
Existing markers on HEAD: none
Per-lane counts:
  CQ: P0=0 P1=1 P2=0 P3=0 Nit=0
  SP: P0=0 P1=0 P2=0 P3=0 Nit=0
  TC: P0=0 P1=0 P2=0 P3=0 Nit=0
Findings (each line-anchored):
  - [CQ P1 #1] src/foo.ts:42 — Inconsistent error handling
Local gates on this HEAD: typecheck=PASS, lint=PASS, test=PASS 100/100
CI status: green
"""
        result = vm.validate_marker(text)
        self.assertFalse(result.ok)
        self.assertIn("do not match per-lane totals", " ".join(result.errors))

    def test_review_marker_per_category_counts_must_match_body(self):
        text = """REVIEW_FINDINGS_claude-code_R1_b8e1d44 TOTAL P0=0 P1=1 P2=0 P3=0 | CQ P0=0 P1=0 P2=0 P3=0 | SP P0=0 P1=1 P2=0 P3=0 | TC P0=0 P1=0 P2=0 P3=0

Vendor: claude-code
Round: 1
HEAD reviewed: b8e1d44e123456789abcdef1234567890abcdef1
Existing markers on HEAD: none
Per-lane counts:
  CQ: P0=0 P1=1 P2=0 P3=0 Nit=0
  SP: P0=0 P1=0 P2=0 P3=0 Nit=0
  TC: P0=0 P1=0 P2=0 P3=0 Nit=0
Findings (each line-anchored):
  - [CQ P1 #1] src/foo.ts:42 — Inconsistent error handling
Local gates on this HEAD: typecheck=PASS, lint=PASS, test=PASS 100/100
CI status: green
"""
        result = vm.validate_marker(text)
        self.assertFalse(result.ok)
        self.assertIn("first-line CQ counts", " ".join(result.errors))

    def test_review_clean_with_p2_fails(self):
        """Self-contradiction: REVIEW_CLEAN can't have P2≥1 (CONTRACT §8 trigger 4)."""
        text = """REVIEW_CLEAN_claude-code_abc1234 TOTAL P0=0 P1=0 P2=1 P3=0 | CQ P0=0 P1=0 P2=1 P3=0 | SP P0=0 P1=0 P2=0 P3=0 | TC P0=0 P1=0 P2=0 P3=0

Vendor: claude-code
HEAD reviewed: abc1234d567890abcdef1234567890abcdef1234
Existing markers on HEAD: none
Per-lane findings:
  CQ: P0=0 P1=0 P2=1 P3=0 Nit=0
  SP: P0=0 P1=0 P2=0 P3=0 Nit=0
  TC: P0=0 P1=0 P2=0 P3=0 Nit=0
Local gates on this HEAD: typecheck=PASS, lint=PASS, test=PASS 100/100
CI status: green
"""
        result = vm.validate_marker(text)
        self.assertFalse(result.ok)
        self.assertIn("P0/P1/P2", " ".join(result.errors).replace(" ", "/").lower() + " ".join(result.errors))

    def test_review_clean_with_existing_marker_field_listed(self):
        """v1.0.5: REVIEW_CLEAN with a prior other-vendor clean marker listed in
        the Existing markers field is the canonical 'second vendor confirms gate'
        shape. Validator accepts it."""
        text = """REVIEW_CLEAN_codex-cli_abc1234 TOTAL P0=0 P1=0 P2=0 P3=0 | CQ P0=0 P1=0 P2=0 P3=0 | SP P0=0 P1=0 P2=0 P3=0 | TC P0=0 P1=0 P2=0 P3=0

Vendor: codex-cli
HEAD reviewed: abc1234d567890abcdef1234567890abcdef1234
Existing markers on HEAD:
  - REVIEW_CLEAN_claude-code_abc1234  (posted 2026-05-26T02:42:25Z)
Per-lane findings:
  CQ: P0=0 P1=0 P2=0 P3=0 Nit=0
  SP: P0=0 P1=0 P2=0 P3=0 Nit=0
  TC: P0=0 P1=0 P2=0 P3=0 Nit=0
Local gates on this HEAD: typecheck=PASS, lint=PASS, test=PASS 100/100
CI status: green
"""
        result = vm.validate_marker(text)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.kind, "REVIEW_CLEAN")

    def test_review_clean_missing_existing_markers_field_fails(self):
        """v1.0.5: REVIEW_CLEAN without the 'Existing markers on HEAD' field is
        a contract violation. This is the field that forces the reviewer to read
        the PR state before posting, enabling /review's gate-satisfied guard and
        preventing stale 'needs another review' closing lines."""
        text = """REVIEW_CLEAN_claude-code_abc1234 TOTAL P0=0 P1=0 P2=0 P3=0 | CQ P0=0 P1=0 P2=0 P3=0 | SP P0=0 P1=0 P2=0 P3=0 | TC P0=0 P1=0 P2=0 P3=0

Vendor: claude-code
HEAD reviewed: abc1234d567890abcdef1234567890abcdef1234
Per-lane findings:
  CQ: P0=0 P1=0 P2=0 P3=0 Nit=0
  SP: P0=0 P1=0 P2=0 P3=0 Nit=0
  TC: P0=0 P1=0 P2=0 P3=0 Nit=0
Local gates on this HEAD: typecheck=PASS, lint=PASS, test=PASS 100/100
CI status: green
"""
        result = vm.validate_marker(text)
        self.assertFalse(result.ok)
        self.assertIn("Existing markers on HEAD", " ".join(result.errors))

    def test_review_findings_missing_existing_markers_field_fails(self):
        """v1.0.5: REVIEW_FINDINGS also requires the 'Existing markers on HEAD'
        field. Even when posting findings, the reviewer must enumerate prior
        markers so the next vendor can see the full state."""
        text = """REVIEW_FINDINGS_claude-code_R1_b8e1d44 TOTAL P0=0 P1=1 P2=0 P3=0 | CQ P0=0 P1=1 P2=0 P3=0 | SP P0=0 P1=0 P2=0 P3=0 | TC P0=0 P1=0 P2=0 P3=0

Vendor: claude-code
Round: 1
HEAD reviewed: b8e1d44e123456789abcdef1234567890abcdef1
Per-lane counts:
  CQ: P0=0 P1=1 P2=0 P3=0 Nit=0
  SP: P0=0 P1=0 P2=0 P3=0 Nit=0
  TC: P0=0 P1=0 P2=0 P3=0 Nit=0
Findings (each line-anchored):
  - [CQ P1 #1] src/foo.ts:42 — Inconsistent error handling
Local gates on this HEAD: typecheck=PASS, lint=PASS, test=PASS 100/100
CI status: green
"""
        result = vm.validate_marker(text)
        self.assertFalse(result.ok)
        self.assertIn("Existing markers on HEAD", " ".join(result.errors))


class TestLoopDone(unittest.TestCase):
    def test_minimal_valid(self):
        text = """LOOP_DONE_codex-cli_aef9999 TOTAL P0=0 P1=0 P2=0 P3=2 | CQ P0=0 P1=0 P2=0 P3=2 | SP P0=0 P1=0 P2=0 P3=0 | TC P0=0 P1=0 P2=0 P3=0

Vendor: codex-cli
HEAD: aef9999d567890abcdef1234567890abcdef1234
Internal rounds taken: 3
Final internal review:
  CQ: P0=0 P1=0 P2=0 P3=2 Nit=1
  SP: P0=0 P1=0 P2=0 P3=0 Nit=0
  TC: P0=0 P1=0 P2=0 P3=0 Nit=0
Gates: typecheck=PASS, lint=PASS, test=PASS 100/100
CI: not yet fired
Commits pushed this loop: aef1111, aef2222, aef9999
"""
        result = vm.validate_marker(text)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.kind, "LOOP_DONE")
        self.assertEqual(result.internal_rounds, 3)

    def test_missing_first_line_counts_fails(self):
        text = """LOOP_DONE_codex-cli_aef9999

Vendor: codex-cli
HEAD: aef9999d567890abcdef1234567890abcdef1234
Internal rounds taken: 3
Final internal review:
  CQ: P0=0 P1=0 P2=0 P3=2 Nit=1
  SP: P0=0 P1=0 P2=0 P3=0 Nit=0
  TC: P0=0 P1=0 P2=0 P3=0 Nit=0
Gates: typecheck=PASS, lint=PASS, test=PASS 100/100
CI: not yet fired
Commits pushed this loop: aef1111, aef2222, aef9999
"""
        result = vm.validate_marker(text)
        self.assertFalse(result.ok)
        self.assertIn("aggregate and per-category P0/P1/P2/P3 counts", " ".join(result.errors))

    def test_first_line_counts_must_match_lane_totals(self):
        text = """LOOP_DONE_codex-cli_aef9999 TOTAL P0=0 P1=0 P2=0 P3=1 | CQ P0=0 P1=0 P2=0 P3=1 | SP P0=0 P1=0 P2=0 P3=0 | TC P0=0 P1=0 P2=0 P3=0

Vendor: codex-cli
HEAD: aef9999d567890abcdef1234567890abcdef1234
Internal rounds taken: 3
Final internal review:
  CQ: P0=0 P1=0 P2=0 P3=2 Nit=1
  SP: P0=0 P1=0 P2=0 P3=0 Nit=0
  TC: P0=0 P1=0 P2=0 P3=0 Nit=0
Gates: typecheck=PASS, lint=PASS, test=PASS 100/100
CI: not yet fired
Commits pushed this loop: aef1111, aef2222, aef9999
"""
        result = vm.validate_marker(text)
        self.assertFalse(result.ok)
        self.assertIn("do not match per-lane totals", " ".join(result.errors))

    def test_blocking_loop_done_counts_fail(self):
        text = """LOOP_DONE_codex-cli_aef9999 TOTAL P0=0 P1=0 P2=1 P3=0 | CQ P0=0 P1=0 P2=1 P3=0 | SP P0=0 P1=0 P2=0 P3=0 | TC P0=0 P1=0 P2=0 P3=0

Vendor: codex-cli
HEAD: aef9999d567890abcdef1234567890abcdef1234
Internal rounds taken: 3
Final internal review:
  CQ: P0=0 P1=0 P2=1 P3=0 Nit=0
  SP: P0=0 P1=0 P2=0 P3=0 Nit=0
  TC: P0=0 P1=0 P2=0 P3=0 Nit=0
Gates: typecheck=PASS, lint=PASS, test=PASS 100/100
CI: not yet fired
Commits pushed this loop: aef1111, aef2222, aef9999
"""
        result = vm.validate_marker(text)
        self.assertFalse(result.ok)
        self.assertIn("LOOP_DONE lane CQ has P0/P1/P2 non-zero", " ".join(result.errors))


class TestKindDetection(unittest.TestCase):
    def test_unknown_first_line(self):
        text = "FOO_BAR_baz\n\nVendor: x\n"
        result = vm.validate_marker(text)
        self.assertFalse(result.ok)
        self.assertIn("unrecognized", " ".join(result.errors).lower())


if __name__ == "__main__":
    unittest.main()
