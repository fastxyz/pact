# Changelog

## v1.0.3 — 2026-05-25

### Docs (clarification, no behavior change for correct agents)
- **`commands/loop.md`** — add a "round-zero check" step that explicitly skips the Coder phase when the latest PR marker is a clean marker (REVIEW_CLEAN / LOOP_DONE) from any vendor AND no unresolved REVIEW_FINDINGS exist. Without this, a strict-vs-lenient reading of step 5a ("Coder phase: implement code, run gates, push") could let a lenient agent push speculative changes when there's nothing to address — which would (a) stale the prior vendor's clean marker, (b) waste compute, (c) risk introducing new bugs the prior vendor would then have to re-flag.
- **`commands/loop.md`** — explicit "Round-zero exit" edge case documenting that `Internal rounds taken: 0` is the correct LOOP_DONE state when a different vendor's clean marker already covers the existing HEAD AND this vendor's self-review also finds it clean. This is the canonical "second vendor confirms first vendor's clean review" path.
- **`commands/loop.md`** — print-to-user note distinguishing the round-zero case from the normal case: when /loop's round-zero check fires AND a different vendor has already posted a clean marker, the merge gate is satisfied immediately; the user should be told that rather than "switch to another vendor's CLI and run /review".
- **`roles/coder.md`** — add a "Trigger (when the Coder is allowed to act)" section enumerating the three conditions under which the Coder may act (unresolved findings, initial R1, same-loop self-review findings). Forbids speculative pushes outside these conditions.

No changes to CONTRACT.md, marker formats, escalation triggers, or merge gate. Existing correct agents continue to work; the clarification removes a reading ambiguity that could cause lenient agents to push speculative commits and stale prior vendor clean markers.

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
