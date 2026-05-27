---
name: review
description: PACT /review — single external multi-lane review of a PR's HEAD. Posts REVIEW_CLEAN or REVIEW_FINDINGS marker. Does not modify code.
---

# /review <PR>

You are running the PACT `/review` command (see `commands/review.md`). Vendor identifier is `claude-code`.

## Required reading

- `https://raw.githubusercontent.com/fastxyz/pact/v1.0.0/CONTRACT.md`
- `https://raw.githubusercontent.com/fastxyz/pact/v1.0.0/roles/reviewer.md`
- `https://raw.githubusercontent.com/fastxyz/pact/v1.0.0/commands/review.md`

## Execution

1. Read PR state (same as `/code` step 1), including the full list of existing markers on the current HEAD.
2. Compute this vendor's R counter: count prior `REVIEW_FINDINGS_claude-code_R*` markers; next R = count + 1.
3. Dispatch three parallel lane sub-agents via the `Agent` tool:
   - CQ: `subagent_type="Explore"`, prompt = "Review the diff of PR <N> HEAD <sha> on lane CQ per fastxyz/pact roles/reviewer.md. Report findings as `[CQ <sev>] <file:line> — <summary>` and per-severity counts. No code changes."
   - SP: similar with lane=SP and the linked spec from the PR description
   - TC: similar with lane=TC, allowed to run gates locally
4. Aggregate findings into CQ/SP/TC per-category counts and all-lane P0/P1/P2/P3 totals.
5. If local CI did not run, run gates via `Bash` (`npm run typecheck && npm run lint && npm test` or the project's equivalent).
6. Emit the marker. The marker first line MUST include aggregate P0/P1/P2/P3 totals, then CQ/SP/TC per-category P0/P1/P2/P3 counts, immediately after the marker title; do not put a bare marker title on the first line:

   **If 0 P0/P1/P2 AND all gates PASS:**

   ```
   REVIEW_CLEAN_claude-code_<short-sha> TOTAL P0=0 P1=0 P2=0 P3=<total-p3> | CQ P0=0 P1=0 P2=0 P3=<cq-p3> | SP P0=0 P1=0 P2=0 P3=<sp-p3> | TC P0=0 P1=0 P2=0 P3=<tc-p3>

   Vendor: claude-code
   HEAD reviewed: <full SHA>
   Existing markers on HEAD:
     - <prior marker title on this HEAD>  (posted <ISO timestamp>)
     - ...
     (Use "none" if no prior markers.)
   Per-lane findings:
     CQ: P0=0 P1=0 P2=0 P3=<w> Nit=<nit>
     SP: P0=0 P1=0 P2=0 P3=<w> Nit=<nit>
     TC: P0=0 P1=0 P2=0 P3=<w> Nit=<nit>
   P3 findings (advisory):
     - [<lane>] <file:line> — <summary>
   Local gates on this HEAD: typecheck=PASS, lint=PASS, test=PASS <n>/<m>
   CI status: <green|red|not fired>
   ```

   **Else:**

   ```
   REVIEW_FINDINGS_claude-code_R<N>_<short-sha> TOTAL P0=<total-p0> P1=<total-p1> P2=<total-p2> P3=<total-p3> | CQ P0=<cq-p0> P1=<cq-p1> P2=<cq-p2> P3=<cq-p3> | SP P0=<sp-p0> P1=<sp-p1> P2=<sp-p2> P3=<sp-p3> | TC P0=<tc-p0> P1=<tc-p1> P2=<tc-p2> P3=<tc-p3>

   Vendor: claude-code
   Round (this vendor's nth findings post on this PR): <N>
   HEAD reviewed: <full SHA>
   Existing markers on HEAD:
     - <prior marker title on this HEAD>  (posted <ISO timestamp>)
     - ...
     (Use "none" if no prior markers.)
   Per-lane counts:
     CQ: P0=<x> P1=<y> P2=<z> P3=<w> Nit=<nit>
     SP: P0=<x> P1=<y> P2=<z> P3=<w> Nit=<nit>
     TC: P0=<x> P1=<y> P2=<z> P3=<w> Nit=<nit>
   Findings (each line-anchored):
     - [CQ P1 #1] apps/foo/bar.ts:42 — <summary>
     - ...
   Local gates on this HEAD: typecheck=<PASS|FAIL>, lint=<PASS|FAIL>, test=<PASS:<n>/<m>|FAIL>
   CI status: <green|red|not fired>
   ```

   Post via `Bash`.

7. If this is the 5th `REVIEW_FINDINGS_claude-code_R*` marker on this PR, also print the escalation notice (CONTRACT §8 trigger 1): "Per-vendor R counter for claude-code has hit 5 on this PR. Escalating to user per CONTRACT §8."

8. Print to user:
   - If CLEAN: "Merge gate needs the other vendor's clean marker on HEAD `<short-sha>`."
   - If FINDINGS: "Findings posted. Run `/code` or `/loop <PR>` in the coder vendor's CLI to address them."
