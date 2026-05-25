# Changelog

## v1.0.2 — 2026-05-25

### Docs (clarification, no behavior change)
- **`commands/code.md`** — clarify that `/code` accepts findings from ANY vendor (different OR same), not only from a cross-vendor REVIEW_FINDINGS marker. Prior wording ("from a different vendor", "from another vendor") could be misread by a strict agent as a hard restriction, breaking composability with `/review` in the same vendor's window. The merge gate (§6) is enforced at the gate, not at the source of findings.
- **`commands/loop.md`** — same clarification on the "ingest cross-vendor findings" step; add an "Equivalence to manual composition" note explaining that `/loop` is the automated form of alternating `/review` + `/code` in one vendor's window, and the two produce semantically equivalent results.

No changes to `CONTRACT.md`, marker formats, escalation triggers, or merge gate. Existing agents continue to work; the clarification only removes a reading ambiguity that could cause stricter agents to refuse valid same-vendor `/code` invocations.

## v1.0.1 — 2026-05-25

### Docs
- **`README.md`** — reframe the primary usage as the URL-only path: prime each session once with "Learn https://github.com/fastxyz/pact", then issue short commands like `/code 282`, `/loop [10] 282`, `/review 282`. No local install needed. The "install as native slash commands" path is demoted to an Optional section for frequent local use. This better matches ephemeral / VPS-hopping / fresh-session workflows where per-machine setup is friction.
- No content changes to `CONTRACT.md`, `roles/`, `commands/`, or `adapters/`. Behavior identical to v1.0.0.

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
