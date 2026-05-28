# /review — Codex CLI prompt template

Substitute `<PR>` before pasting.

---

You are executing PACT (`fastxyz/pact`) `/review` for PR #<PR>. Vendor identifier is `codex-cli`.

## Required reading

- `https://raw.githubusercontent.com/fastxyz/pact/main/CONTRACT.md`
- `https://raw.githubusercontent.com/fastxyz/pact/main/roles/reviewer.md`
- `https://raw.githubusercontent.com/fastxyz/pact/main/commands/review.md`

## Execution

1. Read PR state (`gh pr view`, `gh pr diff`, `gh pr view --comments`, `gh pr checks`), including the full list of existing markers on the current HEAD.
2. Apply the same-HEAD duplicate guard from `commands/review.md` step 3. If it fires, the first paragraph MUST start `TOTAL P0=0 P1=0 P2=0 P3=<prior-total-p3>. P0/P1/P2 are zero;` and no marker is posted.
3. Compute R counter: count prior `REVIEW_FINDINGS_codex-cli_R*` markers on this PR; next R = count + 1.
4. Spawn three concurrent subtasks (or sequential), one per lane (CQ, SP, TC) per `roles/reviewer.md`.
5. Aggregate findings into CQ/SP/TC per-category counts and all-lane P0/P1/P2/P3 totals.
6. If local CI did not run on this HEAD, run gates locally.
7. Emit the marker. The marker first line MUST include aggregate P0/P1/P2/P3 totals, then CQ/SP/TC per-category P0/P1/P2/P3 counts, immediately after the marker title; do not put a bare marker title on the first line:

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
8. If R now equals 5, print the CONTRACT §8 trigger 1 escalation notice.
9. Print to user, deriving the state from `Existing markers on HEAD` plus the marker just posted. The first paragraph MUST start with the aggregate counts:
   - If CLEAN and a different-vendor clean marker already exists on this HEAD: "TOTAL P0=0 P1=0 P2=0 P3=<total-p3>. P0/P1/P2 are zero; merge gate satisfied on HEAD `<short-sha>` (this vendor + prior `<other-vendor>` clean marker). Human authorization required to merge."
   - If CLEAN and no different-vendor clean marker exists yet: "TOTAL P0=0 P1=0 P2=0 P3=<total-p3>. P0/P1/P2 are zero; merge gate needs the other vendor's clean marker on HEAD `<short-sha>`."
   - If FINDINGS: "TOTAL P0=<total-p0> P1=<total-p1> P2=<total-p2> P3=<total-p3>. P0/P1/P2 blockers remain; findings posted. Run `/code` or `/loop <PR>` in the coder vendor's CLI."

## Operate at maximum reasoning level. Anchor every finding to file:line.
