# PACT — Annotated PR Loop Transcript

A worked example of a hypothetical PR going through the PACT cycle. Use this as a reference when learning the marker sequence and the human-orchestration alternation.

## Setup

- Project: `fastxyz/some-app`
- PR: #500 — "feat(auth): add session refresh token rotation"
- Vendors used: `codex-cli` (coder) and `claude-code` (reviewer)
- PACT version: v1.0.7

The author opens two CLI windows:
- **Window A:** Codex CLI inside the project directory
- **Window B:** Claude Code inside the project directory

## Flow A: tight `/loop` + `/review` (the recommended default)

### Turn 1 (Window A): Codex `/loop 500`

The author types `/loop 500` in Codex. Codex:
1. Reads CONTRACT.md, roles/coder.md, roles/reviewer.md, commands/loop.md
2. Reads PR #500 state (HEAD = `a4f7c92...`, no prior markers, CI not fired yet)
3. Enters internal loop. Round 1:
   - Implements the session-refresh logic
   - Runs gates: typecheck PASS, lint PASS, test PASS 247/247
   - Pushes commit `b8e1d44`
   - Self-reviews three lanes: CQ finds 1 P2, SP finds 0, TC finds 0
4. Round 2:
   - Refactors per CQ P2 finding
   - Re-runs gates: all PASS
   - Pushes commit `c9f2e55`
   - Self-reviews: CQ 0, SP 0, TC 0 — clean.
5. Posts marker:

```
LOOP_DONE_codex-cli_c9f2e55 TOTAL P0=0 P1=0 P2=0 P3=1 | CQ P0=0 P1=0 P2=0 P3=1 | SP P0=0 P1=0 P2=0 P3=0 | TC P0=0 P1=0 P2=0 P3=0

Vendor: codex-cli
HEAD: c9f2e55a1b2c3d4e5f6789abcdef0123456789ab
Internal rounds taken: 2
Final internal review:
  CQ: P0=0 P1=0 P2=0 P3=1 Nit=2
  SP: P0=0 P1=0 P2=0 P3=0 Nit=0
  TC: P0=0 P1=0 P2=0 P3=0 Nit=1
Gates: typecheck=PASS, lint=PASS, test=PASS 247/247
CI: not yet fired
Commits pushed this loop: b8e1d44, c9f2e55
```

Codex prints: "TOTAL P0=0 P1=0 P2=0 P3=1. P0/P1/P2 are zero; merge gate (CONTRACT §7) needs a clean marker from a different vendor on HEAD `c9f2e55`. Switch to another vendor's CLI and run `/review 500` (or `/loop 500`)."

### Turn 2 (Window B): Claude Code `/review 500`

The author switches to Window B and types `/review 500`. Claude Code:
1. Reads CONTRACT.md, roles/reviewer.md, commands/review.md
2. Reads PR #500 (HEAD `c9f2e55`, finds the `LOOP_DONE_codex-cli_c9f2e55` marker — Codex has converged internally)
3. Dispatches three parallel sub-agents for CQ, SP, TC lanes
4. SP finds 1 P1: "session refresh doesn't invalidate the old token; allows token replay" at `src/auth/refresh.ts:88`
5. TC finds 1 P2: "no test covers the case where the refresh request races with logout"
6. R counter for claude-code: this is the 1st findings post → R=1
7. Posts marker:

```
REVIEW_FINDINGS_claude-code_R1_c9f2e55 TOTAL P0=0 P1=1 P2=1 P3=0 | CQ P0=0 P1=0 P2=0 P3=0 | SP P0=0 P1=1 P2=0 P3=0 | TC P0=0 P1=0 P2=1 P3=0

Vendor: claude-code
Round (this vendor's nth findings post on this PR): 1
HEAD reviewed: c9f2e55a1b2c3d4e5f6789abcdef0123456789ab
Existing markers on HEAD:
  - LOOP_DONE_codex-cli_c9f2e55  (posted 2026-05-25T12:00:00Z)
Per-lane counts:
  CQ: P0=0 P1=0 P2=0 P3=0 Nit=0
  SP: P0=0 P1=1 P2=0 P3=0 Nit=0
  TC: P0=0 P1=0 P2=1 P3=0 Nit=0
Findings (each line-anchored):
  - [SP P1 #1] src/auth/refresh.ts:88 — refresh path keeps old token valid; permits replay
  - [TC P2 #1] tests/auth/refresh.test.ts — no race-with-logout coverage
Local gates on this HEAD: typecheck=PASS, lint=PASS, test=PASS 247/247
CI status: green
```

Claude Code prints: "TOTAL P0=0 P1=1 P2=1 P3=0. P0/P1/P2 blockers remain; findings posted. Run `/code` or `/loop 500` in the coder vendor's CLI to address them."

### Turn 3 (Window A): Codex `/loop 500`

Author back to Window A. Codex:
1. Reads PR state, finds the new `REVIEW_FINDINGS_claude-code_R1_c9f2e55` marker
2. Enters internal loop with those findings as input. Round 1:
   - Adds explicit old-token invalidation
   - Adds the race-test
   - Gates PASS
   - Pushes commit `d0a1b22`
   - Self-reviews: all lanes clean
3. Posts marker:

```
LOOP_DONE_codex-cli_d0a1b22 TOTAL P0=0 P1=0 P2=0 P3=1 | CQ P0=0 P1=0 P2=0 P3=1 | SP P0=0 P1=0 P2=0 P3=0 | TC P0=0 P1=0 P2=0 P3=0

Vendor: codex-cli
HEAD: d0a1b22a1b2c3d4e5f6789abcdef0123456789ab
Internal rounds taken: 1
Final internal review:
  CQ: P0=0 P1=0 P2=0 P3=1 Nit=2
  SP: P0=0 P1=0 P2=0 P3=0 Nit=0
  TC: P0=0 P1=0 P2=0 P3=0 Nit=0
Gates: typecheck=PASS, lint=PASS, test=PASS 249/249
CI: green
Commits pushed this loop: d0a1b22
```

Codex prints: "TOTAL P0=0 P1=0 P2=0 P3=1. P0/P1/P2 are zero; merge gate (CONTRACT §7) needs a clean marker from a different vendor on HEAD `d0a1b22`. Switch to another vendor's CLI and run `/review 500` (or `/loop 500`)."

### Turn 4 (Window B): Claude Code `/review 500`

Claude Code reviews HEAD `d0a1b22`. All three lanes clean. Posts:

```
REVIEW_CLEAN_claude-code_d0a1b22 TOTAL P0=0 P1=0 P2=0 P3=1 | CQ P0=0 P1=0 P2=0 P3=1 | SP P0=0 P1=0 P2=0 P3=0 | TC P0=0 P1=0 P2=0 P3=0

Vendor: claude-code
HEAD reviewed: d0a1b22a1b2c3d4e5f6789abcdef0123456789ab
Existing markers on HEAD:
  - LOOP_DONE_codex-cli_d0a1b22  (posted 2026-05-25T12:10:00Z)
Per-lane findings:
  CQ: P0=0 P1=0 P2=0 P3=1 Nit=0
  SP: P0=0 P1=0 P2=0 P3=0 Nit=0
  TC: P0=0 P1=0 P2=0 P3=0 Nit=0
P3 findings (advisory):
  - [CQ] src/auth/refresh.ts:42 — consider extracting token-pair builder
Local gates on this HEAD: typecheck=PASS, lint=PASS, test=PASS 249/249
CI status: green
```

Claude Code prints: "TOTAL P0=0 P1=0 P2=0 P3=1. P0/P1/P2 are zero; merge gate satisfied on HEAD `d0a1b22` (this vendor + prior `codex-cli` clean marker). Human authorization required to merge."

### Merge gate satisfied

The PR now has BOTH on HEAD `d0a1b22`:
- `LOOP_DONE_codex-cli_d0a1b22` (codex-cli's clean review)
- `REVIEW_CLEAN_claude-code_d0a1b22` (claude-code's clean review)

The human PR owner can now merge. Total: 4 cross-window turns, 1 cross-vendor round.

## Flow B: granular `/code` + `/review` alternating

Same PR, but the author wants finer manual control:

| Turn | Window | Command | Marker posted |
|---|---|---|---|
| 1 | A (Codex) | `/code 500` | `CODE_DONE_codex-cli_b8e1d44` |
| 2 | B (Claude) | `/review 500` | `REVIEW_FINDINGS_claude-code_R1_b8e1d44` (CQ P2 found) |
| 3 | A (Codex) | `/code 500` | `CODE_DONE_codex-cli_c9f2e55` |
| 4 | B (Claude) | `/review 500` | `REVIEW_FINDINGS_claude-code_R2_c9f2e55` (SP P1 + TC P2 found) |
| 5 | A (Codex) | `/code 500` | `CODE_DONE_codex-cli_d0a1b22` |
| 6 | B (Claude) | `/review 500` | `REVIEW_CLEAN_claude-code_d0a1b22` |
| 7 | A (Codex) | `/review 500` | `REVIEW_CLEAN_codex-cli_d0a1b22` |

Now the gate is satisfied with TWO `REVIEW_CLEAN` markers (one per vendor) on the same HEAD. Note that flow B needs the extra Turn 7 (Codex reviews its own pushed HEAD) because `CODE_DONE` is not a clean marker.

Flow B uses 7 turns instead of 4 but gives the author per-step manual oversight. Use when `/loop` is misbehaving or when you want to inspect each push before the next review.

## Escalation example

If Claude Code's `/review` keeps finding new P1s across 5 rounds without convergence (`R1`, `R2`, …, `R5`), the 5th `/review` invocation triggers CONTRACT §8 trigger 1. Claude Code posts the R5 marker AND prints an escalation notice to the user. The human PR owner is expected to intervene — drop the PR, split into smaller PRs, or call in a human reviewer.
