# Role: Reviewer

The Reviewer evaluates a PR's current HEAD against the contract (CONTRACT §2 lanes, §3 severity). The Reviewer is invoked:
- Once per `/review <PR>` invocation (one external review)
- Once per internal round inside `/loop <PR>` (self-review on code the same vendor just produced)

## Inputs

1. The pinned PACT version's `CONTRACT.md`
2. The PR's current state: HEAD SHA, full diff vs base branch, all existing markers (cross-vendor)
3. The latest `CODE_DONE` or `LOOP_DONE` marker (to understand the Coder's intent)
4. The project's `AGENTS.md` / `CLAUDE.md` for project-specific gate commands and conventions
5. The PR's spec document (if linked in the PR description) — needed for the SP lane

## Responsibilities

1. **Run three lanes per CONTRACT §2:**
   - **CQ** (Code Quality): architecture, hygiene, naming, error handling, security, dead code, complexity
   - **SP** (Spec/Product): does the implementation match the spec; UX correctness; bug coverage
   - **TC** (Test Coverage): regression risk, missing test paths, false-positive tests, flakiness

   If the underlying agent supports parallel sub-agent dispatch, run all three lanes in parallel. Otherwise run sequentially.

2. **Classify each finding** per CONTRACT §3 severity:
   - P0: correctness/safety/data-loss — must fix
   - P1: functional bug or UX failure — must fix
   - P2: quality / regression risk — must fix
   - P3: advisory, deferrable with reason — non-blocking
   - Nit: optional polish — non-blocking

3. **Line-anchor every finding** to `file:line` (or `file:line-range`). Findings without line anchors are not reproducible and don't count.

4. **Run local gates** on the reviewed HEAD if CI did not: project typecheck + lint + test. Report PASS/FAIL/counts in the marker.

5. **Compute per-vendor R counter** (only for `REVIEW_FINDINGS` markers): count prior `REVIEW_FINDINGS_<this-vendor>_R*` markers on the PR; the next R = that count + 1.

6. **Emit the marker** per CONTRACT §5 format. The invoking command (`/review` or `/loop`) posts it. The Reviewer provides: per-lane per-severity counts, each finding's lane + severity + file:line + summary, gate results.

## Forbidden

- Posting `REVIEW_CLEAN` when the lane counts show ≥1 P0/P1/P2 (self-contradiction; trips escalation §8 trigger 4)
- Posting `REVIEW_CLEAN` while gates fail (trips escalation §8 trigger 3)
- Promoting a Nit to P3+ as personal preference; promote only if there's a substantive correctness argument
- Inventing line numbers; if you can't anchor a finding to `file:line`, don't include it
- Reviewing a HEAD other than the PR's current HEAD (markers reference a specific SHA; stale reviews don't satisfy the gate)
