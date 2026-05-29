# PACT — Agent Review Contract

> **Merge gate (non-negotiable).** Any PR merged in a PACT-governed project must have **P0 = P1 = P2 = 0** from independent reviews by at least **two different LLM vendors**, each at the highest reasoning level available.

How you reach that state is your choice. Write the code by hand. Use the commands in this repo. Follow your own discipline. The gate is the only non-negotiable rule.

## How to use it (minimal-friction path)

You do not need to install or copy anything. The recommended flow:

**1. Open two LLM windows, one per vendor** (e.g., Codex CLI in window A, Claude Code in window B). Each window has access to your repo via `gh` CLI (any Fast / GitHub-authorized session).

**2. Prime each window once, at the start of the session, with a single sentence:**

> Learn https://github.com/fastxyz/pact

The agent fetches the README, then `CONTRACT.md`, `roles/*.md`, `commands/*.md`, and the vendor-specific adapter under `adapters/<vendor>/` for its own kind (e.g., Claude Code fetches `adapters/claude-code/*.md`, Codex CLI fetches `adapters/codex-cli/*.md`). It now knows the contract, the marker formats, the escalation rules, and how to dispatch its multi-lane review.

**3. From then on, type short commands:**

| Command | Effect |
|---|---|
| `/code 282` | one coding pass on PR 282, no internal review; posts `CODE_DONE_<vendor>_<sha>` |
| `/loop 282` | code↔self-review converge on PR 282, internal cap N=5; posts `LOOP_DONE_<vendor>_<sha>` |
| `/loop [10] 282` | same, with internal cap N=10 |
| `/review 282` | one external multi-lane review of PR 282; posts `REVIEW_CLEAN_<vendor>_<sha>` or `REVIEW_FINDINGS_<vendor>_R<N>_<sha>` |

**4. Alternate windows** until both vendors have posted a clean marker (`LOOP_DONE` or `REVIEW_CLEAN`) on the **same HEAD SHA**. That satisfies the merge gate.

**5. Authorize the merge.** Human stays in the merge loop — PACT does not auto-merge.

You only re-prime ("Learn https://github.com/fastxyz/pact") at the start of a new session. Within a session, the agent has everything in context.

## What's here

| File / dir | Purpose |
|---|---|
| **[`CONTRACT.md`](CONTRACT.md)** | The canonical rules — lanes, severity, marker formats, escalation, merge gate. |
| **[`roles/`](roles/)** | What the Coder and Reviewer roles do, step-by-step. Vendor-agnostic. |
| **[`commands/`](commands/)** | What `/code`, `/loop`, and `/review` do. Vendor-agnostic. |
| **[`adapters/`](adapters/)** | Per-vendor implementations (Claude Code, Codex CLI). |
| **[`examples/`](examples/)** | An annotated PR-loop transcript showing the markers in action. |
| **[`docs/standalone-cli-design.md`](docs/standalone-cli-design.md)** | Design roadmap for turning PACT into a standalone CLI/tooling package. |
| **[`scripts/validate-marker.py`](scripts/validate-marker.py)** | Stdlib Python parser/validator for any PACT marker. Useful for CI. |
| **[`scripts/pact_format_marker.py`](scripts/pact_format_marker.py)** | Stdlib JSON-to-marker formatter that renders current-schema `CODE_DONE`, `LOOP_DONE`, `REVIEW_CLEAN`, and `REVIEW_FINDINGS` comments and validates them before printing. |
| **[`scripts/pact_format_event.py`](scripts/pact_format_event.py)** | Deterministic Slack/Markdown formatter for structured PACT progress events. |
| **[`scripts/pact_progress_watch.py`](scripts/pact_progress_watch.py)** | `progress.jsonl` watcher that emits only new formatted PACT status blocks. |
| **[`CHANGELOG.md`](CHANGELOG.md)** | Semver releases. |

## The merge gate, restated

A PR is mergeable when **two different vendors** have each posted a clean marker (`LOOP_DONE` or `REVIEW_CLEAN`) on the **same HEAD SHA**. Anything else — `CODE_DONE` alone, one vendor's `LOOP_DONE` without a cross-check, gates failing — does NOT satisfy the gate.

Every review or loop status must start with the aggregate severity counts: `TOTAL P0=<n> P1=<n> P2=<n> P3=<n>.` If P0/P1/P2 are all zero, say that in the first paragraph before merge-gate or next-action text.

The contract is what keeps both vendors honest. No agent invokes another. You are the orchestrator, alternating between vendor windows.

## Optional: install as native slash commands

If you work consistently on one machine and want `/code` / `/loop` / `/review` to appear as registered Claude Code slash commands (with tab-completion, no per-session prime), you can copy the adapter files locally:

```bash
git clone https://github.com/fastxyz/pact ~/work/pact
cp ~/work/pact/adapters/claude-code/{code,loop,review}.md ~/.claude/skills/
# Restart Claude Code.
```

For Codex CLI, paste the prompt template from `adapters/codex-cli/<command>.md` (substituting `<PR>` and `<N>`) as your first message.

This is a convenience for frequent local use. For ephemeral sessions, VPS-hopping, or any setup where per-machine configuration is friction, **skip this and stay with the URL-only flow above**.

## Optional: pin a version

For projects that want reproducibility (CI references a specific contract version), add to the project's `AGENTS.md` / `CLAUDE.md`:

> This project follows `fastxyz/pact` v1.x. The merge gate (§1 of the contract) applies.

Pin a specific version (`v1.0.0`) if you need strict reproducibility. For day-to-day use, the unversioned URL above is fine — `main` is the latest semver release.

## Validating markers

```bash
python3 scripts/validate-marker.py < my-marker.txt
# OK: REVIEW_CLEAN from claude-code on d0a1b22
```

Exit code 0 = valid; 1 = invalid (errors on stderr). Useful for a GitHub Action that lints new PR comments for marker conformance.

## Formatting markers

Agents and wrappers should render markers from JSON instead of hand-writing comment text. This prevents drift such as `CQ PASS | SP PASS | TC PASS` shorthand after the contract requires explicit per-lane counts.

```bash
python3 scripts/pact_format_marker.py --marker-json '{
  "kind":"REVIEW_CLEAN",
  "vendor":"claude-code",
  "head":"d0a1b22c0ffee1234567890abcdef1234567890ab",
  "existing_markers":[{"title":"LOOP_DONE_codex-cli_d0a1b22c0ffee1234567890abcdef1234567890ab"}],
  "lanes":{"CQ":{"p0":0,"p1":0,"p2":0,"p3":0},"SP":{"p0":0,"p1":0,"p2":0,"p3":0},"TC":{"p0":0,"p1":0,"p2":0,"p3":0}},
  "gates":"typecheck=PASS, lint=PASS, test=PASS",
  "ci_status":"green"
}' > marker.txt
python3 scripts/validate-marker.py marker.txt
gh pr comment 282 --body-file marker.txt
```

`pact_format_marker.py` validates its own output by default and exits non-zero rather than printing a malformed marker.

## Progress reporting helpers

PACT itself is GitHub-comment based, but operators often want compact Slack-style progress updates while detached agent loops run. Use structured JSON events plus the deterministic formatter instead of asking an LLM to improvise status text.

A `/loop` or `/review` runner can append JSON lines to `progress.jsonl`:

```json
{"event":"round","round":2,"head":"ad29edbc7668606ddf8a43bf9651445af0a62691","p0":0,"p1":0,"p2":1,"p3":0,"summary":"Found one blocking issue.","findings":[{"severity":"P2","lane":"SP","loc":"apps/api/public/assets/chat-widget.js:5059-5072","issue":"Concise issue text."}]}
```

Format one event:

```bash
python3 scripts/pact_format_event.py \
  --repo fastxyz/fast-shop \
  --pr 443 \
  --vendor-label Codex \
  --mode loop \
  --event-file event.json
```

Watch a detached run and emit only new updates:

```bash
python3 scripts/pact_progress_watch.py \
  --run-dir .pact/runs/pr-443-codex-loop-20260529T211003Z \
  --repo fastxyz/fast-shop \
  --pr 443 \
  --vendor codex-cli \
  --vendor-label Codex \
  --mode loop \
  --session pact-codex-pr443-loop \
  --stats .pact/stats.json
```

Clean final loop rounds are merged with `LOOP_DONE` into one block. Every PR, commit, marker comment, and file/line reference is emitted as a clickable GitHub link when enough data is present.

## Versioning

PACT follows semver. Breaking changes to marker formats or escalation rules bump the major version. Adding new commands or new adapters bumps the minor version.

## License

(TBD — to be set by Grigore when publishing.)
