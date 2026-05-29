#!/usr/bin/env python3
"""Watch a PACT progress.jsonl file and print deterministic Slack updates.

Designed for Hermes cron `no_agent=True`: stdout is delivered verbatim, empty
stdout is silent. The script never asks an LLM to format status.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import subprocess
import sys
import time
from typing import Any

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
FORMATTER_PATH = SCRIPT_DIR / "pact_format_event.py"
spec = importlib.util.spec_from_file_location("pact_format_event", FORMATTER_PATH)
formatter = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(formatter)  # type: ignore[union-attr]


def read_json(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: pathlib.Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_events(lines: list[str]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for raw in lines:
        try:
            ev = json.loads(raw)
        except Exception:
            continue
        if ev.get("event") == "started":
            continue
        events.append(ev)
    return events


def is_clean_round(ev: dict[str, Any]) -> bool:
    if ev.get("event") != "round":
        return False
    try:
        return int(ev.get("p0", 0)) == 0 and int(ev.get("p1", 0)) == 0 and int(ev.get("p2", 0)) == 0
    except Exception:
        return False


def matches_done(round_ev: dict[str, Any], done_ev: dict[str, Any]) -> bool:
    return (
        done_ev.get("event") == "loop_done"
        and str(done_ev.get("round")) == str(round_ev.get("round"))
        and str(done_ev.get("head")) == str(round_ev.get("head"))
    )


def session_alive(session: str | None) -> bool:
    if not session:
        return False
    proc = subprocess.run(
        ["tmux", "has-session", "-t", session],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


def log_tail(log_path: pathlib.Path, chars: int = 1800) -> str:
    if not log_path.exists():
        return ""
    lines = [l for l in log_path.read_text(errors="replace").splitlines() if l.strip()]
    return " | ".join(lines[-10:])[-chars:]


def update_stats(stats_path: pathlib.Path | None, pr: str, vendor: str, event: dict[str, Any], mode: str) -> None:
    if not stats_path:
        return
    stats = read_json(stats_path)
    if not stats:
        stats = {"schema_version": 1, "prs": {}}
    pr_entry = stats.setdefault("prs", {}).setdefault(str(pr), {})
    key = "last_progress_event" if mode == "loop" else f"last_{vendor}_review_event"
    pr_entry[key] = event
    if event.get("event") in ("round", "review_clean", "review_findings"):
        rounds = pr_entry.setdefault("review_rounds_by_vendor", {})
        if mode == "loop" and event.get("round") is not None:
            rounds[vendor] = max(int(rounds.get(vendor, 0)), int(event.get("round") or 0))
        elif mode == "review":
            rounds[vendor] = int(rounds.get(vendor, 0)) + 1
        pr_entry.setdefault("blocking_findings_by_vendor", {})[vendor] = {
            "p0": event.get("p0"),
            "p1": event.get("p1"),
            "p2": event.get("p2"),
            "p3": event.get("p3"),
            "findings": event.get("findings") or [],
        }
    if event.get("event") in ("loop_done", "review_clean"):
        marker_event = "LOOP_DONE" if event.get("event") == "loop_done" else "REVIEW_CLEAN"
        marker = {
            "vendor": vendor,
            "head": event.get("head"),
            "event": marker_event,
            "url": event.get("commentUrl") or event.get("comment_url"),
        }
        markers = pr_entry.setdefault("clean_markers", [])
        if marker not in markers:
            markers.append(marker)
    stats["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    write_json(stats_path, stats)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Watch a PACT progress.jsonl and print new Slack updates")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", required=True)
    parser.add_argument("--vendor", required=True, help="PACT vendor token, e.g. codex-cli")
    parser.add_argument("--vendor-label", required=True, help="Human label, e.g. Codex")
    parser.add_argument("--mode", required=True, choices=["loop", "review"])
    parser.add_argument("--session", help="tmux session to monitor")
    parser.add_argument("--progress", default="progress.jsonl")
    parser.add_argument("--state", default="watch_state.json")
    parser.add_argument("--log", help="log filename/path; default <vendor>.log fallback")
    parser.add_argument("--stats", help="optional stats.json path")
    args = parser.parse_args(argv)

    run_dir = pathlib.Path(args.run_dir)
    progress = pathlib.Path(args.progress)
    if not progress.is_absolute():
        progress = run_dir / progress
    state_path = pathlib.Path(args.state)
    if not state_path.is_absolute():
        state_path = run_dir / state_path
    log_path = pathlib.Path(args.log) if args.log else run_dir / f"{args.vendor}.log"
    if not log_path.is_absolute():
        log_path = run_dir / log_path
    stats_path = pathlib.Path(args.stats) if args.stats else None

    state = read_json(state_path)
    last_line = int(state.get("last_line", 0))
    lines = progress.read_text(errors="replace").splitlines() if progress.exists() else []
    new_events = parse_events(lines[last_line:])

    pending = state.pop("pending_clean_round", None)
    events = ([pending] if pending else []) + new_events
    consumed: set[int] = set()
    messages: list[str] = []
    alive = session_alive(args.session)

    for idx, ev in enumerate(events):
        if idx in consumed:
            continue
        etype = ev.get("event")

        if args.mode == "loop" and is_clean_round(ev):
            done_idx = next((j for j in range(idx + 1, len(events)) if matches_done(ev, events[j])), None)
            if done_idx is not None:
                done = events[done_idx]
                messages.append(formatter.format_event(args.repo, args.pr, args.vendor_label, args.mode, done))
                update_stats(stats_path, args.pr, args.vendor, done, args.mode)
                consumed.add(done_idx)
                state["done"] = True
            elif alive:
                # Hold clean round briefly so the later loop_done marker can be merged into one message.
                state["pending_clean_round"] = ev
            else:
                messages.append(formatter.format_event(args.repo, args.pr, args.vendor_label, args.mode, ev))
                update_stats(stats_path, args.pr, args.vendor, ev, args.mode)
            continue

        if etype in ("round", "loop_done", "blocked", "review_clean", "review_findings"):
            messages.append(formatter.format_event(args.repo, args.pr, args.vendor_label, args.mode, ev))
            update_stats(stats_path, args.pr, args.vendor, ev, args.mode)
            if etype in ("loop_done", "blocked", "review_clean", "review_findings"):
                state["done"] = True
        else:
            messages.append(f"**PACT {formatter.pr_link(args.repo, args.pr)}** {args.vendor_label} event\n```{json.dumps(ev, sort_keys=True)[:1000]}```")

    state["last_line"] = len(lines)

    if not state.get("done") and not state.get("reported_exit") and args.session and not alive:
        messages.append(
            f"**PACT {formatter.pr_link(args.repo, args.pr)}** {args.vendor_label} worker exited before final progress event\n"
            + log_tail(log_path)
        )
        state["reported_exit"] = True

    write_json(state_path, state)
    if messages:
        print("\n\n".join(messages))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
