#!/usr/bin/env python3
"""Format PACT progress events for Slack.

This script is intentionally deterministic: agents should write structured JSON
progress events, then call this formatter instead of improvising user-facing
PACT status text.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any
from urllib.parse import quote


def _int(event: dict[str, Any], key: str, default: int = 0) -> int:
    value = event.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def count_values(event: dict[str, Any]) -> str:
    return f"{_int(event, 'p0')}/{_int(event, 'p1')}/{_int(event, 'p2')}/{_int(event, 'p3')}"


def pr_link(repo: str, pr: int | str) -> str:
    return f"<https://github.com/{repo}/pull/{pr}|#{pr}>"


def commit_link(repo: str, head: str | None) -> str:
    if not head:
        return ""
    return f"<https://github.com/{repo}/commit/{head}|{str(head)[:8]}>"


def github_loc_link(repo: str, loc: str | None, head: str | None) -> str:
    if not loc or not head:
        return loc or ""
    # Accept: path/file.ts:10, path/file.ts:10-20, path/file.ts:L10-L20
    m = re.match(
        r"^(?P<path>[^\s:]+):(L)?(?P<start>\d+)(?:[-:](?:L)?(?P<end>\d+))?$",
        str(loc).strip(),
    )
    if not m:
        return str(loc)
    path = m.group("path")
    start = m.group("start")
    end = m.group("end")
    anchor = f"#L{start}" + (f"-L{end}" if end else "")
    url = f"https://github.com/{repo}/blob/{head}/{quote(path, safe='/')}{anchor}"
    label = f"{path}:{start}" + (f"-{end}" if end else "")
    return f"<{url}|{label}>"


def _finding_text(repo: str, event: dict[str, Any], item: Any) -> str:
    if not isinstance(item, dict):
        return f"• {item}"
    sev = str(item.get("severity") or item.get("sev") or "Issue").upper()
    lane = item.get("lane")
    loc = item.get("loc") or item.get("location") or item.get("file") or ""
    issue = (
        item.get("issue")
        or item.get("summary")
        or item.get("description")
        or item.get("text")
        or ""
    )
    where = github_loc_link(repo, str(loc), event.get("head")) if loc else ""
    lane_txt = f"[{lane}] " if lane else ""
    detail = " — ".join(str(x) for x in (where, issue) if x)
    return f"• **{sev}**: {lane_txt}{detail}".rstrip()


def finding_lines(repo: str, event: dict[str, Any]) -> list[str]:
    findings = event.get("findings") or []
    if isinstance(findings, dict):
        findings = [findings]
    if not isinstance(findings, list):
        findings = [findings]
    return [_finding_text(repo, event, item) for item in findings[:20]]


def has_nonzero_issue(event: dict[str, Any]) -> bool:
    return any(_int(event, key) != 0 for key in ("p0", "p1", "p2", "p3"))


def marker_suffix(event: dict[str, Any], label: str) -> str:
    url = event.get("commentUrl") or event.get("comment_url")
    return f" [<{url}|{label}>]" if url else ""


def format_event(repo: str, pr: int | str, vendor_label: str, mode: str, event: dict[str, Any]) -> str:
    """Return the canonical user-facing Slack/Markdown block for one PACT event."""
    event_type = event.get("event")
    head = event.get("head")
    lines: list[str]

    if mode == "loop":
        if event_type == "loop_done":
            header = (
                f"**PACT {pr_link(repo, pr)}** {vendor_label} loop Round "
                f"**R{event.get('round')} / CLEAN**{marker_suffix(event, 'LOOP_DONE comment')}"
            )
        elif event_type == "blocked":
            header = (
                f"**PACT {pr_link(repo, pr)}** {vendor_label} loop Round "
                f"**R{event.get('round')} / BLOCKED**"
            )
        else:
            header = f"**PACT {pr_link(repo, pr)}** {vendor_label} loop Round **R{event.get('round')}**"
    elif mode == "review":
        if event_type == "review_clean":
            header = (
                f"**PACT {pr_link(repo, pr)}** {vendor_label} review **CLEAN**"
                f"{marker_suffix(event, 'REVIEW_CLEAN comment')}"
            )
        elif event_type == "review_findings":
            header = (
                f"**PACT {pr_link(repo, pr)}** {vendor_label} review **FINDINGS**"
                f"{marker_suffix(event, 'REVIEW_FINDINGS comment')}"
            )
        else:
            header = f"**PACT {pr_link(repo, pr)}** {vendor_label} review"
    else:
        header = f"**PACT {pr_link(repo, pr)}** {vendor_label} {mode}"

    lines = [header, f"**P0/P1/P2/P3 = {count_values(event)}**"]
    commit = commit_link(repo, str(head) if head else None)
    if commit:
        lines.append(f"Reviewed commit: {commit}")

    # Clean messages intentionally omit obvious filler. Non-clean messages may keep
    # a one-line summary for context, followed by itemized findings.
    f_lines = finding_lines(repo, event)
    if has_nonzero_issue(event) and event.get("summary"):
        lines.append(str(event["summary"]))
    lines.extend(f_lines)
    return "\n".join(lines)


def load_event(args: argparse.Namespace) -> dict[str, Any]:
    if args.event_json:
        return json.loads(args.event_json)
    if args.event_file and args.event_file != "-":
        with open(args.event_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return json.load(sys.stdin)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Format one PACT JSON progress event for Slack")
    parser.add_argument("--repo", required=True, help="OWNER/REPO, e.g. fastxyz/fast-shop")
    parser.add_argument("--pr", required=True, help="PR number")
    parser.add_argument("--vendor-label", required=True, help="Human vendor name, e.g. Codex or Claude")
    parser.add_argument("--mode", required=True, choices=["loop", "review"], help="PACT event family")
    parser.add_argument("--event-file", help="JSON event file; use - for stdin")
    parser.add_argument("--event-json", help="Inline JSON event")
    args = parser.parse_args(argv)
    print(format_event(args.repo, args.pr, args.vendor_label, args.mode, load_event(args)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
