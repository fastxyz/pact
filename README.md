# PACT — Agent Review Contract

> **Merge gate (non-negotiable).** Any PR merged in a PACT-governed project must have **P0 = P1 = P2 = 0** from independent reviews by at least **two different LLM vendors**, each at the highest reasoning level available.

How you reach that state is your choice. Write the code by hand. Use the commands in this repo. Follow your own discipline. The gate is the only non-negotiable rule.

## What's here

| File / dir | Purpose |
|---|---|
| **[`CONTRACT.md`](CONTRACT.md)** | The canonical rules — lanes, severity, marker formats, escalation, merge gate. Read this once; reference forever. |
| **[`roles/`](roles/)** | What the Coder and Reviewer roles do, step-by-step. Vendor-agnostic. |
| **[`commands/`](commands/)** | What `/code`, `/loop`, and `/review` do. Vendor-agnostic. |
| **[`adapters/`](adapters/)** | Per-vendor implementations of the three commands. `claude-code` and `codex-cli` ship in v1. |
| **[`examples/`](examples/)** | An annotated PR-loop transcript showing the markers in action. |
| **[`scripts/validate-marker.py`](scripts/validate-marker.py)** | Stdlib Python parser/validator for any PACT marker. Useful for CI. |
| **[`CHANGELOG.md`](CHANGELOG.md)** | Semver releases. Projects pin a version. |

## The three commands

| Command | What it does | Posts marker |
|---|---|---|
| `/code <PR>` | one coding pass; no internal review | `CODE_DONE_<vendor>_<sha>` |
| `/loop <PR> [N]` | internal code↔self-review converge, default cap N=5 | `LOOP_DONE_<vendor>_<sha>` |
| `/review <PR>` | one external multi-lane review | `REVIEW_CLEAN_<vendor>_<sha>` or `REVIEW_FINDINGS_<vendor>_R<N>_<sha>` |

The merge gate is satisfied when **two different vendors** each post a clean marker (`LOOP_DONE` or `REVIEW_CLEAN`) on the **same HEAD SHA**.

## How to use it

1. Open two CLI windows, one per vendor (e.g., Codex CLI in window A, Claude Code in window B).
2. In one window, run `/code` or `/loop` to push code.
3. In the other, run `/review` to verify.
4. Alternate until both vendors have posted a clean marker on the same HEAD.
5. Authorize the merge.

No agent invokes another. You are the orchestrator. The contract is what keeps both sides honest.

## Installation

### Claude Code

```bash
cp adapters/claude-code/{code,loop,review}.md ~/.claude/skills/
```

Restart Claude Code. The skills appear as `/code`, `/loop`, `/review`.

### Codex CLI

Paste the prompt template from `adapters/codex-cli/<command>.md` into Codex CLI as your first message, substituting `<PR>` and (for `/loop`) `<N>`. A wrapper script is on the v2 roadmap.

## Opting your project in

In your project's `AGENTS.md` (or `CLAUDE.md`):

> This project follows `fastxyz/pact` v1.x. The merge gate (§1 of the contract) applies.

Pin a specific version (`v1.0.0`) if you need reproducibility.

## Validating markers

```bash
python3 scripts/validate-marker.py < my-marker.txt
# OK: REVIEW_CLEAN from claude-code on d0a1b22
```

Exit code 0 = valid; 1 = invalid (errors on stderr).

## Versioning

PACT follows semver. Breaking changes to marker formats or escalation rules bump the major version. Adding new commands or new adapters bumps the minor version.

## License

(TBD — to be set by Grigore when publishing.)
