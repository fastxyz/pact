# Changelog

## Unreleased

### Schema clarification

- `REVIEW_CLEAN` and `REVIEW_FINDINGS` first lines now must include aggregate P0/P1/P2/P3 totals immediately after the marker title. The validator rejects review markers that omit these first-line counts or whose first-line totals disagree with the per-lane counts. This is intended to make severity visible at a glance in PR comments, especially for Codex-style review summaries.

## v1.0.6 — 2026-05-26

### Fix (v1.0.5 round-zero check was wrong; this version replaces it)

**v1.0.5 added a "round-zero check" to `commands/review.md` that fired when a different-vendor REVIEW_CLEAN/LOOP_DONE existed on the current HEAD and exited without posting** — on the premise that "the merge gate is already satisfied." That premise is wrong: CONTRACT §1 requires TWO different vendors' clean markers, not one. A different-vendor clean marker alone leaves the gate at 1/2; this vendor's review is exactly what produces the second vote.

If v1.0.5's round-zero had actually fired on a real PR with only one prior vendor's clean marker, the running vendor would have exited without contributing the second vote and the merge gate would have been stuck at 1/2 indefinitely. The check was caught by the very PR audit it was meant to validate (fastxyz/fast-shop, 2026-05-26) before any agent applied it in anger.

**v1.0.6 replaces v1.0.5's broken round-zero check with a narrow same-HEAD duplicate guard** (`commands/review.md` step 3):

- Fires ONLY when `REVIEW_CLEAN_<this-vendor>_<sha>` or `LOOP_DONE_<this-vendor>_<sha>` already exists on the current HEAD AND there are no unresolved REVIEW_FINDINGS. The condition is about THIS vendor's own prior coverage, not about another vendor's.
- When it fires, this vendor has already cast its vote on this HEAD; re-posting is a same-vendor duplicate, not a fresh vote. The guard prints "This vendor already cleared HEAD `<sha>` at <prior timestamp>" plus a state-derived merge-gate status line and exits without posting.
- A different vendor's clean marker on its own NEVER triggers the guard — this vendor's review is still needed to contribute the second vote.

**The actual fix for the original "wrong closing line" failure mode is kept**: the required `Existing markers on HEAD:` field in CONTRACT §5 (REVIEW_CLEAN + REVIEW_FINDINGS schemas, unchanged from v1.0.5) plus the state-derived closing-line spec in `commands/review.md` step 9 (three cases enumerated). When the agent enumerates prior markers as a precondition for posting, the closing line cannot template "needs another vendor" while a prior vendor's marker is sitting in the body.

**Asymmetric with `/loop`'s round-zero on purpose.** `/loop`'s round-zero exit POSTS LOOP_DONE (with `Internal rounds taken: 0`) because that IS how a /loop invocation contributes to the merge gate when there's no Coder work to do — a real review with zero rounds, still a vote. `/review`'s same-HEAD duplicate guard is different: this vendor has ALREADY posted its vote on this HEAD; re-posting would be a same-vendor duplicate. v1.0.5 modeled `/review`'s round-zero on `/loop`'s shape but dropped the "still post the marker" half, which is the half that contributes to the gate.

No changes to marker schemas, lane structure, severities, escalation triggers, or the merge gate definition. The `Existing markers on HEAD` field and validator enforcement remain (v1.0.5).

## v1.0.5 — 2026-05-26

### Docs + schema (closes a recurring failure mode)

**Failure mode.** An agent runs `/review <PR>` without first reading the PR's existing markers, posts its own `REVIEW_CLEAN`, and closes with the templated "needs another vendor's clean marker on this HEAD" line — even when a different vendor's clean marker already covers that exact HEAD and the merge gate was satisfied minutes earlier. Wasted compute, duplicate marker on the PR, and a closing line that contradicts the actual gate state. Observed at least twice in real use of `fastxyz/pact` v1.0.4 (claude-code adapter).

**Two changes close it:**

- **`commands/review.md`** — add a "round-zero check" step (new step 3, between "read PR state" and "compute R counter") that mirrors `/loop`'s round-zero check from v1.0.3. If a different-vendor `REVIEW_CLEAN_*` or `LOOP_DONE_*` exists on the current HEAD AND no unresolved `REVIEW_FINDINGS_*` exist anywhere on the PR, the merge gate is already satisfied — print "Merge gate satisfied on HEAD `<sha>`" and EXIT. Do not run the lanes, do not run local gates, do not post a marker. Force-override available via `/review <PR> --cross-verify` when the user has a substantive reason to triple-check.
- **`commands/review.md`** — closing line MUST be derived from the marker body's `Existing markers on HEAD` field, never from a template. Three cases enumerated (this clean + prior clean = gate satisfied; this clean alone = needs other vendor; findings = run /code or /loop).
- **`CONTRACT.md`** — add the required `Existing markers on HEAD <sha>:` field to both `REVIEW_CLEAN` and `REVIEW_FINDINGS` marker schemas. The field enumerates every prior marker on the current HEAD (with ISO timestamps). The reviewer cannot post a marker without producing this list, which forces the round-zero check to be observed in practice even if the agent skipped step 3.

The two changes are intentionally redundant — they catch the same failure at different layers. The round-zero check prevents the redundant marker in the common case. The required schema field catches the residual case where the agent forgets the round-zero check too: it cannot fill out the marker body without enumerating prior markers, which surfaces the duplicate before posting.

**Round-zero exit added to edge cases.** `commands/review.md` Edge cases now explicitly documents the round-zero exit as the canonical "second vendor confirms gate already met" path — the symmetric counterpart to `/loop`'s round-zero exit from v1.0.3. `/review` is the appropriate command when the user wants a literal review with no Coder phase even allocated; the round-zero check makes the two effectively equivalent when there's nothing to review.

No changes to marker types, severities, lanes, escalation triggers, or the merge gate definition. v1.0.4 agents continue to work; v1.0.5 adds a required field (gracefully detectable — missing field is a contract violation, validator updated).

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
