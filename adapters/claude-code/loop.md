---
name: loop
description: PACT /loop — internal code↔self-review converge for one vendor. Default max 5 internal rounds; override via [N] in either position. Posts LOOP_DONE marker on success.
---

# /loop <PR> [N]

You are running the PACT `/loop` command (see `commands/loop.md`). Vendor identifier is `claude-code`.

## Required reading

Same as `/code` plus:
- `https://raw.githubusercontent.com/fastxyz/pact/main/roles/reviewer.md`
- `https://raw.githubusercontent.com/fastxyz/pact/main/commands/loop.md`

## Argument parsing

The user invokes one of:
- `/loop 282` → PR=282, cap N=5 (default)
- `/loop 282 [10]` → PR=282, cap N=10
- `/loop [10] 282` → PR=282, cap N=10

Parsing rule: any bare positive integer ≤ 999999 = PR number. Any `[X]` with X a positive integer = cap N. If both present in either order, both are honored. If neither bracket is present, N defaults to 5.

## Execution

1. Read PR state (same as `/code` step 1) plus the latest unresolved `REVIEW_FINDINGS` from a vendor other than `claude-code` (if any) for ingestion.
2. Set `n = 0` (internal round counter).
3. Enter the internal loop:
   - `n += 1`
   - Print round-start status for the user before coding: `TOTAL P0=<a> P1=<b> P2=<c> P3=<d>. Round <n> starting: remaining review counts | CQ P0=<cq-p0> P1=<cq-p1> P2=<cq-p2> P3=<cq-p3> | SP P0=<sp-p0> P1=<sp-p1> P2=<sp-p2> P3=<sp-p3> | TC P0=<tc-p0> P1=<tc-p1> P2=<tc-p2> P3=<tc-p3>.` Round 1 uses ingested unresolved findings, later rounds use the prior self-review.
   - **Coder phase:** implement / fix per `roles/coder.md`. Run gates. If gates fail, halt the loop and report (do NOT post `LOOP_DONE`); user takes over manually. If gates pass, push the commits.
   - **Self-review phase:** dispatch three parallel lane sub-agents via the `Agent` tool:
     - CQ subagent: `subagent_type="Explore"`, prompt = "Review the diff of PR <N> HEAD <sha> on lane CQ per fastxyz/pact roles/reviewer.md. Report findings as `[CQ <sev>] <file:line> — <summary>` + per-severity counts. No code changes."
     - SP subagent: similar with lane=SP and access to the linked spec
     - TC subagent: similar with lane=TC, allowed to run gates locally
   - Aggregate the three subagent reports. Compute per-lane per-severity totals.
   - Print round-finished status immediately after review aggregation: `TOTAL P0=<a> P1=<b> P2=<c> P3=<d>. Round <n> finished: remaining review counts | CQ P0=<cq-p0> P1=<cq-p1> P2=<cq-p2> P3=<cq-p3> | SP P0=<sp-p0> P1=<sp-p1> P2=<sp-p2> P3=<sp-p3> | TC P0=<tc-p0> P1=<tc-p1> P2=<tc-p2> P3=<tc-p3>.` Then say either `P0/P1/P2 are zero; preparing LOOP_DONE.` or `P0/P1/P2 blockers remain; another round is needed.`
   - If 0 P0/P1/P2 AND gates green: exit the loop → go to step 4.
   - If `n >= N`: halt per CONTRACT §8 trigger 5. Do NOT post `LOOP_DONE`. Print: "TOTAL P0=<a> P1=<b> P2=<c> P3=<d>. P0/P1/P2 blockers remain; loop cap N=<N> exhausted at HEAD `<short-sha>`. The latest pushes are on the PR. Switch vendors and run `/review` or run `/code` to attempt a manual fix."
   - Else: feed the self-review findings back into the Coder phase; continue.
4. Post the marker using this exact template:

```
LOOP_DONE_claude-code_<short-sha> TOTAL P0=0 P1=0 P2=0 P3=<total-p3> | CQ P0=0 P1=0 P2=0 P3=<cq-p3> | SP P0=0 P1=0 P2=0 P3=<sp-p3> | TC P0=0 P1=0 P2=0 P3=<tc-p3>

Vendor: claude-code
HEAD: <full SHA>
Internal rounds taken: <n>
Final internal review:
  CQ: P0=0 P1=0 P2=0 P3=<w> Nit=<nit>
  SP: P0=0 P1=0 P2=0 P3=<w> Nit=<nit>
  TC: P0=0 P1=0 P2=0 P3=<w> Nit=<nit>
Gates: typecheck=PASS, lint=PASS, test=PASS <n>/<m>
CI: <link or "not yet fired">
Commits pushed this loop: <comma-separated short SHAs>
```

Post via `Bash` (`gh pr comment <PR> --body-file <tempfile>`).

5. Print to user: "TOTAL P0=0 P1=0 P2=0 P3=<total-p3>. P0/P1/P2 are zero; merge gate (CONTRACT §7) needs a clean marker from a different vendor on HEAD `<short-sha>`. Switch to another vendor's CLI and run `/review <PR>` (or `/loop <PR>`)."

## Notes

- Internal Coder ↔ Reviewer alternation does NOT post intermediate markers. Only the final `LOOP_DONE` (or halt notice) is observable on the PR.
- On halt (cap exhausted or gates failing): the user explicitly takes over. The skill does not auto-retry.
