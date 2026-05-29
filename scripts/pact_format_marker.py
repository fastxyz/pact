#!/usr/bin/env python3
"""Deterministically render PACT PR markers from structured JSON.

Agents should write marker facts as JSON, then call this script instead of
hand-writing marker text. The output is designed to pass scripts/validate-marker.py
and to match CONTRACT.md §5.5's current marker schema.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

LANES = ("CQ", "SP", "TC")
COUNT_KEYS = ("p0", "p1", "p2", "p3")
SEVERITY_TO_KEY = {"P0": "p0", "P1": "p1", "P2": "p2", "P3": "p3", "NIT": "nit", "NITPICK": "nit"}
MARKER_KINDS = {"CODE_DONE", "LOOP_DONE", "REVIEW_CLEAN", "REVIEW_FINDINGS"}
VENDOR_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


class MarkerError(ValueError):
    """Raised when marker input cannot produce a valid PACT marker."""


def _upper_kind(value: Any) -> str:
    kind = str(value or "").strip().upper()
    if kind not in MARKER_KINDS:
        raise MarkerError(f"unsupported marker kind: {value!r}")
    return kind


def _vendor(value: Any) -> str:
    vendor = str(value or "").strip()
    if not VENDOR_RE.fullmatch(vendor):
        raise MarkerError("vendor must match [a-z0-9][a-z0-9-]*")
    return vendor


def _head(value: Any) -> str:
    head = str(value or "").strip().lower()
    if not SHA_RE.fullmatch(head):
        raise MarkerError("head must be a 7-40 character lowercase hex SHA")
    return head


def _int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise MarkerError(f"expected integer count, got {value!r}") from exc
    if result < 0:
        raise MarkerError(f"counts must be non-negative, got {result}")
    return result


def _count_from_mapping(mapping: dict[str, Any], key: str) -> int:
    return _int(mapping.get(key, mapping.get(key.upper(), 0)))


def _empty_lane_counts() -> dict[str, dict[str, int]]:
    return {lane: {"p0": 0, "p1": 0, "p2": 0, "p3": 0, "nit": 0} for lane in LANES}


def normalize_lanes(payload: dict[str, Any]) -> dict[str, dict[str, int]]:
    """Return per-lane counts, computing from findings when lanes are omitted."""

    lanes = _empty_lane_counts()
    raw_lanes = payload.get("lanes")
    if raw_lanes:
        if not isinstance(raw_lanes, dict):
            raise MarkerError("lanes must be a mapping keyed by CQ/SP/TC")
        for lane in LANES:
            raw = raw_lanes.get(lane) or raw_lanes.get(lane.lower()) or {}
            if not isinstance(raw, dict):
                raise MarkerError(f"lane {lane} counts must be an object")
            lanes[lane] = {
                "p0": _count_from_mapping(raw, "p0"),
                "p1": _count_from_mapping(raw, "p1"),
                "p2": _count_from_mapping(raw, "p2"),
                "p3": _count_from_mapping(raw, "p3"),
                "nit": _count_from_mapping(raw, "nit"),
            }
        return lanes

    findings = payload.get("findings") or []
    if isinstance(findings, dict):
        findings = [findings]
    if not isinstance(findings, list):
        raise MarkerError("findings must be a list or object")
    for item in findings:
        if not isinstance(item, dict):
            continue
        lane = str(item.get("lane") or "").strip().upper()
        if lane not in lanes:
            raise MarkerError(f"finding has invalid lane {lane!r}; expected CQ/SP/TC")
        sev = str(item.get("severity") or item.get("sev") or "").strip().upper()
        if sev not in SEVERITY_TO_KEY:
            raise MarkerError(f"finding has invalid severity {sev!r}; expected P0/P1/P2/P3/Nit")
        lanes[lane][SEVERITY_TO_KEY[sev]] += 1
    return lanes


def total_counts(lanes: dict[str, dict[str, int]]) -> dict[str, int]:
    return {key: sum(lanes[lane][key] for lane in LANES) for key in COUNT_KEYS}


def counts_text(counts: dict[str, int]) -> str:
    return f"P0={counts['p0']} P1={counts['p1']} P2={counts['p2']} P3={counts['p3']}"


def title_counts(lanes: dict[str, dict[str, int]]) -> str:
    totals = total_counts(lanes)
    return " | ".join(
        [f"TOTAL {counts_text(totals)}"]
        + [f"{lane} {counts_text(lanes[lane])}" for lane in LANES]
    )


def lane_rows(lanes: dict[str, dict[str, int]]) -> list[str]:
    return [
        f"  {lane}: {counts_text(lanes[lane])} Nit={lanes[lane]['nit']}"
        for lane in LANES
    ]


def _listish(value: Any) -> str:
    if value is None:
        return "not recorded"
    if isinstance(value, str):
        return value.strip() or "not recorded"
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        if not value:
            return "none"
        parts = []
        for item in value:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("command") or item.get("title") or "item")
                status = str(item.get("status") or item.get("conclusion") or "").strip()
                detail = str(item.get("detail") or item.get("url") or item.get("summary") or "").strip()
                text = name
                if status:
                    text += f"={status}"
                if detail:
                    text += f" ({detail})"
                parts.append(text)
            else:
                parts.append(str(item))
        return ", ".join(parts)
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items()) or "none"
    return str(value)


def existing_markers_text(value: Any) -> list[str]:
    if value is None:
        raise MarkerError("review markers require existing_markers")
    if isinstance(value, str):
        raw = value.strip()
        if not raw or raw.lower() == "none":
            return ["Existing markers on HEAD: none"]
        return ["Existing markers on HEAD:", f"  - {raw}"]
    if isinstance(value, list):
        if not value:
            return ["Existing markers on HEAD: none"]
        lines = ["Existing markers on HEAD:"]
        for item in value:
            if isinstance(item, dict):
                title = str(item.get("title") or item.get("marker") or "").strip()
                if not title:
                    raise MarkerError("existing marker objects require title")
                posted = str(item.get("posted") or item.get("createdAt") or item.get("created_at") or "").strip()
                suffix = f"  (posted {posted})" if posted else ""
                lines.append(f"  - {title}{suffix}")
            else:
                lines.append(f"  - {str(item).strip()}")
        return lines
    raise MarkerError("existing_markers must be a string, list, or null")


def _advisory_findings(payload: dict[str, Any]) -> list[dict[str, Any]]:
    findings = payload.get("findings") or payload.get("p3_findings") or []
    if isinstance(findings, dict):
        findings = [findings]
    if not isinstance(findings, list):
        return []
    return [item for item in findings if isinstance(item, dict) and str(item.get("severity") or item.get("sev") or "").upper() in {"P3", "NIT", "NITPICK"}]


def findings_lines(payload: dict[str, Any], *, advisory_only: bool = False) -> list[str]:
    findings = _advisory_findings(payload) if advisory_only else payload.get("findings") or []
    if isinstance(findings, dict):
        findings = [findings]
    if not isinstance(findings, list) or not findings:
        return []

    counters: dict[tuple[str, str], int] = {}
    lines: list[str] = []
    for item in findings:
        if not isinstance(item, dict):
            continue
        lane = str(item.get("lane") or "").strip().upper() or "?"
        sev = str(item.get("severity") or item.get("sev") or "").strip().upper() or "Issue"
        if sev in {"NIT", "NITPICK"}:
            sev = "Nit"
        key = (lane, sev)
        counters[key] = counters.get(key, 0) + 1
        loc = str(item.get("loc") or item.get("location") or item.get("file") or "").strip()
        summary = str(item.get("summary") or item.get("issue") or item.get("description") or item.get("text") or "").strip()
        detail = " — ".join(part for part in (loc, summary) if part)
        lines.append(f"  - [{lane} {sev} #{counters[key]}] {detail}".rstrip())
    return lines


def marker_title(kind: str, vendor: str, head: str, payload: dict[str, Any], lanes: dict[str, dict[str, int]]) -> str:
    if kind == "CODE_DONE":
        return f"CODE_DONE_{vendor}_{head}"
    if kind == "REVIEW_FINDINGS":
        round_num = _int(payload.get("round") or payload.get("r"), default=0)
        if round_num <= 0:
            raise MarkerError("REVIEW_FINDINGS requires positive round")
        return f"REVIEW_FINDINGS_{vendor}_R{round_num}_{head} {title_counts(lanes)}"
    return f"{kind}_{vendor}_{head} {title_counts(lanes)}"


def ensure_clean_allowed(kind: str, lanes: dict[str, dict[str, int]]) -> None:
    totals = total_counts(lanes)
    if kind in {"LOOP_DONE", "REVIEW_CLEAN"} and any(totals[key] for key in ("p0", "p1", "p2")):
        raise MarkerError(f"{kind} cannot contain P0/P1/P2 findings")


def format_code_done(payload: dict[str, Any], vendor: str, head: str) -> str:
    lines = [
        f"CODE_DONE_{vendor}_{head}",
        "",
        f"Vendor: {vendor}",
        f"HEAD: {head}",
        f"Responding to: {_listish(payload.get('responding_to') or payload.get('responding'))}",
        f"Commits pushed: {_listish(payload.get('commits') or payload.get('commits_pushed'))}",
        f"Gates: {_listish(payload.get('gates'))}",
        f"CI: {_listish(payload.get('ci') or payload.get('ci_status'))}",
    ]
    return "\n".join(lines) + "\n"


def format_loop_done(payload: dict[str, Any], vendor: str, head: str, lanes: dict[str, dict[str, int]]) -> str:
    rounds = _int(payload.get("internal_rounds") or payload.get("internal_rounds_taken"), default=-1)
    if rounds < 0:
        raise MarkerError("LOOP_DONE requires internal_rounds")
    lines = [
        marker_title("LOOP_DONE", vendor, head, payload, lanes),
        "",
        f"Vendor: {vendor}",
        f"HEAD: {head}",
        f"Internal rounds taken: {rounds}",
        "Final internal review:",
        *lane_rows(lanes),
        f"Gates: {_listish(payload.get('gates') or payload.get('local_gates'))}",
        f"CI: {_listish(payload.get('ci') or payload.get('ci_status'))}",
        f"Commits pushed this loop: {_listish(payload.get('commits') or payload.get('commits_pushed'))}",
    ]
    return "\n".join(lines) + "\n"


def format_review(payload: dict[str, Any], kind: str, vendor: str, head: str, lanes: dict[str, dict[str, int]]) -> str:
    lines = [marker_title(kind, vendor, head, payload, lanes), "", f"Vendor: {vendor}"]
    if kind == "REVIEW_FINDINGS":
        round_num = _int(payload.get("round") or payload.get("r"), default=0)
        if round_num <= 0:
            raise MarkerError("REVIEW_FINDINGS requires positive round")
        lines.append(f"Round: {round_num}")
    lines.append(f"HEAD reviewed: {head}")
    lines.extend(existing_markers_text(payload.get("existing_markers") or payload.get("existingMarkers")))
    lines.append("Per-lane findings:" if kind == "REVIEW_CLEAN" else "Per-lane counts:")
    lines.extend(lane_rows(lanes))

    if kind == "REVIEW_CLEAN":
        advisory = findings_lines(payload, advisory_only=True)
        if advisory:
            lines.append("P3 findings (advisory):")
            lines.extend(advisory)
    else:
        lines.append("Findings (each line-anchored):")
        lines.extend(findings_lines(payload) or ["  - none"])

    lines.append(f"Local gates on this HEAD: {_listish(payload.get('local_gates') or payload.get('gates'))}")
    lines.append(f"CI status: {_listish(payload.get('ci_status') or payload.get('ci'))}")
    return "\n".join(lines) + "\n"


def format_marker(payload: dict[str, Any]) -> str:
    kind = _upper_kind(payload.get("kind") or payload.get("marker_kind"))
    vendor = _vendor(payload.get("vendor"))
    head = _head(payload.get("head") or payload.get("sha"))

    if kind == "CODE_DONE":
        return format_code_done(payload, vendor, head)

    lanes = normalize_lanes(payload)
    ensure_clean_allowed(kind, lanes)

    if kind == "LOOP_DONE":
        return format_loop_done(payload, vendor, head, lanes)
    if kind in {"REVIEW_CLEAN", "REVIEW_FINDINGS"}:
        return format_review(payload, kind, vendor, head, lanes)
    raise MarkerError(f"unsupported marker kind: {kind}")


def load_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.marker_json:
        payload = json.loads(args.marker_json)
    elif args.marker_file and args.marker_file != "-":
        payload = json.loads(Path(args.marker_file).read_text(encoding="utf-8"))
    else:
        payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        raise MarkerError("marker payload must be a JSON object")
    return payload


def validate_with_local_script(marker: str) -> None:
    validator = Path(__file__).with_name("validate-marker.py")
    spec = importlib.util.spec_from_file_location("validate_marker", validator)
    if spec is None or spec.loader is None:
        raise MarkerError(f"could not load validator at {validator}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    result = module.validate_marker(marker)
    if not result.ok:
        raise MarkerError("rendered marker failed validation: " + "; ".join(result.errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a schema-valid PACT marker from JSON")
    parser.add_argument("--marker-json", help="Inline marker JSON payload")
    parser.add_argument("--marker-file", help="Marker JSON file; use - or omit for stdin")
    parser.add_argument("--no-validate", action="store_true", help="Do not validate rendered marker before printing")
    args = parser.parse_args(argv)

    try:
        marker = format_marker(load_payload(args))
        if not args.no_validate:
            validate_with_local_script(marker)
    except (json.JSONDecodeError, OSError, MarkerError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(marker, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
