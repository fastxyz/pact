# /review — Codex CLI prompt template

Substitute `<PR>` before pasting.

---

You are executing PACT (`fastxyz/pact`) `/review` for PR #<PR>. Vendor identifier is `codex-cli`.

## Required reading

- `https://raw.githubusercontent.com/fastxyz/pact/v1.0.0/CONTRACT.md`
- `https://raw.githubusercontent.com/fastxyz/pact/v1.0.0/roles/reviewer.md`
- `https://raw.githubusercontent.com/fastxyz/pact/v1.0.0/commands/review.md`

## Execution

1. Read PR state (`gh pr view`, `gh pr diff`, `gh pr view --comments`, `gh pr checks`), including the full list of existing markers on the current HEAD.
2. Compute R counter: count prior `REVIEW_FINDINGS_codex-cli_R*` markers on this PR; next R = count + 1.
3. Spawn three concurrent subtasks (or sequential), one per lane (CQ, SP, TC) per `roles/reviewer.md`.
4. Aggregate findings into CQ/SP/TC per-category counts and all-lane P0/P1/P2/P3 totals.
5. If local CI did not run on this HEAD, run gates locally.
6. Emit the marker. The marker first line MUST include aggregate P0/P1/P2/P3 totals, then CQ/SP/TC per-category P0/P1/P2/P3 counts, immediately after the marker title; do not put a bare marker title on the first line:

   **If 0 P0/P1/P2 AND all gates PASS:**

   ```
   REVIEW_CLEAN_codex-cli_<short-sha> TOTAL P0=0 P1=0 P2=0 P3=<total-p3> | CQ P0=0 P1=0 P2=0 P3=<cq-p3> | SP P0=0 P1=0 P2=0 P3=<sp-p3> | TC P0=0 P1=0 P2=0 P3=<tc-p3>

   Vendor: codex-cli
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
   REVIEW_FINDINGS_codex-cli_R<N>_<short-sha> TOTAL P0=<total-p0> P1=<total-p1> P2=<total-p2> P3=<total-p3> | CQ P0=<cq-p0> P1=<cq-p1> P2=<cq-p2> P3=<cq-p3> | SP P0=<sp-p0> P1=<sp-p1> P2=<sp-p2> P3=<sp-p3> | TC P0=<tc-p0> P1=<tc-p1> P2=<tc-p2> P3=<tc-p3>

   Vendor: codex-cli
   Round: <N>
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

   Post via `gh pr comment <PR> --body-file <tempfile>`.

7. If R now equals 5, print the CONTRACT §8 trigger 1 escalation notice.
8. Print to user: if CLEAN → "Merge gate needs the other vendor's clean marker on HEAD `<short-sha>`." If FINDINGS → "Findings posted. Run `/code` or `/loop <PR>` in the coder vendor's CLI."

## Operate at maximum reasoning level. Anchor every finding to file:line.
