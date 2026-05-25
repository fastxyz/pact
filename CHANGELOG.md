# Changelog

## v1.0.0 — 2026-05-25

Initial release.

### Contract
- `CONTRACT.md` — canonical rules: 3 lanes (CQ/SP/TC), 5 severities (P0/P1/P2/P3/Nit), 4 marker types (CODE_DONE, LOOP_DONE, REVIEW_CLEAN, REVIEW_FINDINGS), escalation triggers, disagreement protocol, merge gate.
- `roles/coder.md`, `roles/reviewer.md` — vendor-agnostic role definitions.
- `commands/code.md`, `commands/loop.md`, `commands/review.md` — vendor-agnostic command specs.

### Adapters
- `adapters/claude-code/` — Claude Code skill files for `/code`, `/loop`, `/review`.
- `adapters/codex-cli/` — Codex CLI prompt templates for `/code`, `/loop`, `/review`.

### Tooling
- `scripts/validate-marker.py` — stdlib Python marker validator with unittest suite.

### Docs
- `README.md` — leads with the merge gate; installation + opt-in instructions.
- `examples/annotated-pr-loop-transcript.md` — worked example of tight (`/loop` + `/review`) and granular (`/code` + `/review`) flows.
