"""Validate a PACT marker against CONTRACT.md §5.5 schema.

Usage:
    python3 validate-marker.py < marker.txt
    python3 validate-marker.py marker.txt

Exit codes:
    0 — marker is valid
    1 — marker is invalid (errors printed to stderr)
    2 — usage error
"""
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional


MARKER_KINDS = ("CODE_DONE", "LOOP_DONE", "REVIEW_CLEAN", "REVIEW_FINDINGS")
LANES = ("CQ", "SP", "TC")
SEVERITIES = ("P0", "P1", "P2", "P3", "Nit")


@dataclass
class ValidationResult:
    ok: bool
    kind: Optional[str] = None
    vendor: Optional[str] = None
    head_short: Optional[str] = None
    head_full: Optional[str] = None
    round: Optional[int] = None
    internal_rounds: Optional[int] = None
    errors: List[str] = field(default_factory=list)


def validate_marker(text: str) -> ValidationResult:
    lines = [ln.rstrip() for ln in text.strip().splitlines()]
    result = ValidationResult(ok=True)
    if not lines:
        result.ok = False
        result.errors.append("empty marker")
        return result

    # Parse title line
    title = lines[0]
    m = re.match(
        r"^(CODE_DONE|LOOP_DONE|REVIEW_CLEAN|REVIEW_FINDINGS)_([a-z0-9][a-z0-9-]*)(?:_R(\d+))?_([0-9a-f]{7,40})$",
        title,
    )
    if not m:
        result.ok = False
        result.errors.append(f"unrecognized marker title: {title!r}")
        return result
    result.kind = m.group(1)
    result.vendor = m.group(2)
    round_str = m.group(3)
    result.head_short = m.group(4)

    if result.kind == "REVIEW_FINDINGS" and round_str is None:
        result.ok = False
        result.errors.append("REVIEW_FINDINGS title must include _R<N>")
    if result.kind != "REVIEW_FINDINGS" and round_str is not None:
        result.ok = False
        result.errors.append(f"{result.kind} title must not include _R<N>")
    if round_str:
        result.round = int(round_str)

    # Parse body lines into a key->value mapping for top-level fields
    body = lines[1:]
    fields_map = {}
    for ln in body:
        m2 = re.match(r"^([A-Z][A-Za-z ]+):\s*(.*)$", ln)
        if m2:
            fields_map[m2.group(1).strip()] = m2.group(2).strip()

    # Common required fields
    if "Vendor" not in fields_map:
        result.ok = False
        result.errors.append("missing required field: Vendor")
    elif fields_map["Vendor"] != result.vendor:
        result.ok = False
        result.errors.append(
            f"Vendor field ({fields_map['Vendor']!r}) does not match title vendor ({result.vendor!r})"
        )

    head_key = "HEAD" if result.kind in ("CODE_DONE", "LOOP_DONE") else "HEAD reviewed"
    if head_key not in fields_map:
        result.ok = False
        result.errors.append(f"missing required field: {head_key}")
    else:
        result.head_full = fields_map[head_key]
        if not re.fullmatch(r"[0-9a-f]{7,40}", result.head_full):
            result.ok = False
            result.errors.append(f"{head_key} field is not a hex SHA")
        elif not result.head_full.startswith(result.head_short):
            result.ok = False
            result.errors.append(
                f"{head_key} ({result.head_full!r}) doesn't start with title short SHA ({result.head_short!r})"
            )

    # Kind-specific checks
    if result.kind == "LOOP_DONE":
        if "Internal rounds taken" not in fields_map:
            result.ok = False
            result.errors.append("LOOP_DONE missing: Internal rounds taken")
        else:
            try:
                result.internal_rounds = int(fields_map["Internal rounds taken"])
            except ValueError:
                result.ok = False
                result.errors.append("Internal rounds taken is not an integer")

    if result.kind == "REVIEW_CLEAN":
        # Verify per-lane counts all have P0=P1=P2=0
        lane_rx = re.compile(r"^\s+(CQ|SP|TC): P0=(\d+) P1=(\d+) P2=(\d+) P3=(\d+) Nit=(\d+)$")
        for ln in body:
            m3 = lane_rx.match(ln)
            if m3:
                p0, p1, p2 = int(m3.group(2)), int(m3.group(3)), int(m3.group(4))
                if p0 or p1 or p2:
                    result.ok = False
                    result.errors.append(
                        f"REVIEW_CLEAN lane {m3.group(1)} has P0/P1/P2 non-zero (P0={p0} P1={p1} P2={p2}); use REVIEW_FINDINGS instead"
                    )

    # v1.0.5: REVIEW markers MUST enumerate existing markers on the current
    # HEAD. The field forces the reviewer to read the PR state before posting,
    # which both enables /review's round-zero check (commands/review.md step 3)
    # and prevents stale "needs another vendor" closing lines when the merge
    # gate is already satisfied by a prior vendor's clean marker.
    if result.kind in ("REVIEW_CLEAN", "REVIEW_FINDINGS"):
        if "Existing markers on HEAD" not in fields_map:
            result.ok = False
            result.errors.append(
                f"{result.kind} missing required field: 'Existing markers on HEAD' "
                "(v1.0.5 schema; list other-vendor markers first, or 'none')"
            )

    return result


def main(argv: List[str]) -> int:
    if len(argv) > 2:
        sys.stderr.write(__doc__)
        return 2
    if len(argv) == 2:
        try:
            text = open(argv[1], "r", encoding="utf-8").read()
        except OSError as e:
            sys.stderr.write(f"cannot read {argv[1]}: {e}\n")
            return 2
    else:
        text = sys.stdin.read()

    result = validate_marker(text)
    if result.ok:
        print(f"OK: {result.kind} from {result.vendor} on {result.head_short}")
        return 0
    sys.stderr.write(f"INVALID: {result.kind or '?'}\n")
    for err in result.errors:
        sys.stderr.write(f"  - {err}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
