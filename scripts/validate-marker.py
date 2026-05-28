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
        r"^(CODE_DONE|LOOP_DONE|REVIEW_CLEAN|REVIEW_FINDINGS)_([a-z0-9][a-z0-9-]*)(?:_R(\d+))?_([0-9a-f]{7,40})(?: (.*))?$",
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
    first_line_summary = m.group(5)
    first_line_counts = None
    first_line_lane_counts = {}
    severity_summary_rx = re.compile(
        r"^TOTAL P0=(\d+) P1=(\d+) P2=(\d+) P3=(\d+)"
        r" \| CQ P0=(\d+) P1=(\d+) P2=(\d+) P3=(\d+)"
        r" \| SP P0=(\d+) P1=(\d+) P2=(\d+) P3=(\d+)"
        r" \| TC P0=(\d+) P1=(\d+) P2=(\d+) P3=(\d+)$"
    )

    if result.kind in ("LOOP_DONE", "REVIEW_CLEAN", "REVIEW_FINDINGS"):
        if first_line_summary is None:
            result.ok = False
            result.errors.append(f"{result.kind} title line must include aggregate and per-category P0/P1/P2/P3 counts")
        else:
            m_counts = severity_summary_rx.match(first_line_summary)
            if not m_counts:
                result.ok = False
                result.errors.append(
                    f"{result.kind} title line must use: TOTAL P0=<n> P1=<n> P2=<n> P3=<n> | "
                    "CQ P0=<n> P1=<n> P2=<n> P3=<n> | "
                    "SP P0=<n> P1=<n> P2=<n> P3=<n> | "
                    "TC P0=<n> P1=<n> P2=<n> P3=<n>"
                )
            else:
                values = [int(m_counts.group(i)) for i in range(1, 17)]
                first_line_counts = tuple(values[0:4])
                first_line_lane_counts = {
                    "CQ": tuple(values[4:8]),
                    "SP": tuple(values[8:12]),
                    "TC": tuple(values[12:16]),
                }
    elif first_line_summary is not None:
        result.ok = False
        result.errors.append(f"{result.kind} title line must not include severity counts")

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

    if result.kind in ("LOOP_DONE", "REVIEW_CLEAN", "REVIEW_FINDINGS"):
        lane_rx = re.compile(r"^\s+(CQ|SP|TC): P0=(\d+) P1=(\d+) P2=(\d+) P3=(\d+) Nit=(\d+)$")
        lane_totals = [0, 0, 0, 0]
        lane_counts = {}
        for ln in body:
            m3 = lane_rx.match(ln)
            if not m3:
                continue
            lane = m3.group(1)
            p0, p1, p2, p3 = (int(m3.group(i)) for i in range(2, 6))
            lane_counts[lane] = (p0, p1, p2, p3)
            lane_totals[0] += p0
            lane_totals[1] += p1
            lane_totals[2] += p2
            lane_totals[3] += p3
            if result.kind in ("LOOP_DONE", "REVIEW_CLEAN") and (p0 or p1 or p2):
                result.ok = False
                if result.kind == "REVIEW_CLEAN":
                    result.errors.append(
                        f"REVIEW_CLEAN lane {lane} has P0/P1/P2 non-zero (P0={p0} P1={p1} P2={p2}); use REVIEW_FINDINGS instead"
                    )
                else:
                    result.errors.append(
                        f"LOOP_DONE lane {lane} has P0/P1/P2 non-zero (P0={p0} P1={p1} P2={p2}); do not post LOOP_DONE with blockers"
                    )
        if set(lane_counts) != set(LANES):
            result.ok = False
            result.errors.append(f"{result.kind} must include one per-lane count row for each of CQ, SP, and TC")
        if first_line_counts is not None and tuple(lane_totals) != first_line_counts:
            result.ok = False
            result.errors.append(
                f"{result.kind} first-line TOTAL counts P0/P1/P2/P3={first_line_counts} do not match per-lane totals {tuple(lane_totals)}"
            )
        for lane in LANES:
            if lane in first_line_lane_counts and lane in lane_counts and first_line_lane_counts[lane] != lane_counts[lane]:
                result.ok = False
                result.errors.append(
                    f"{result.kind} first-line {lane} counts {first_line_lane_counts[lane]} do not match body counts {lane_counts[lane]}"
                )

    # v1.0.5: REVIEW markers MUST enumerate existing markers on the current
    # HEAD. The field forces the reviewer to read the PR state before posting,
    # which both enables /review's gate-satisfied guard (commands/review.md step 3)
    # and prevents stale "needs another review" closing lines when the merge
    # gate is already satisfied by two independent clean reviews on the HEAD.
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
