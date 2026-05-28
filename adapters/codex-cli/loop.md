# /loop — Codex CLI prompt template

Substitute `<PR>` (required) and `<N>` (optional, default 5) before pasting.

---

You are executing PACT (`fastxyz/pact`) `/loop` for PR #<PR>, with internal-rounds cap N=<N>. Vendor identifier is `codex-cli`.

## Required reading

Same as `/code` plus:
- `https://raw.githubusercontent.com/fastxyz/pact/v1.1.0/roles/reviewer.md`
- `https://raw.githubusercontent.com/fastxyz/pact/v1.1.0/commands/loop.md`

## Argument parsing

`[N]` in CONTRACT syntax is the max internal rounds (default 5). For this paste, N=<N> is already substituted.

## Execution

1. Read PR state (same as `/code` step 1).
2. Ingest the latest unresolved `REVIEW_FINDINGS` from a vendor other than `codex-cli` (if any).
3. Set internal round counter `n = 0`.
4. Enter the internal loop:
   - `n += 1`
   - Print round-start status for the user before coding: `TOTAL P0=<a> P1=<b> P2=<c> P3=<d>. Round <n> starting: remaining review counts | CQ P0=<cq-p0> P1=<cq-p1> P2=<cq-p2> P3=<cq-p3> | SP P0=<sp-p0> P1=<sp-p1> P2=<sp-p2> P3=<sp-p3> | TC P0=<tc-p0> P1=<tc-p1> P2=<tc-p2> P3=<tc-p3>.` Round 1 uses ingested unresolved findings, later rounds use the prior self-review.
   - **Coder phase:** implement per `roles/coder.md`. Run gates. If gates fail, HALT (do not post `LOOP_DONE`). If gates pass, push.
   - **Self-review phase:** spawn three concurrent subtasks (or run sequentially if your Codex version lacks concurrency), one per lane:
     - CQ subtask: "Review PR <PR> HEAD <sha> diff on lane CQ per fastxyz/pact roles/reviewer.md. Report `[CQ <sev>] <file:line> — <summary>` + per-severity counts. No code changes."
     - SP subtask: similar with lane SP, including the spec from PR description
     - TC subtask: similar with lane TC, may run local gates
   - Aggregate. Print round-finished status immediately after review aggregation: `TOTAL P0=<a> P1=<b> P2=<c> P3=<d>. Round <n> finished: remaining review counts | CQ P0=<cq-p0> P1=<cq-p1> P2=<cq-p2> P3=<cq-p3> | SP P0=<sp-p0> P1=<sp-p1> P2=<sp-p2> P3=<sp-p3> | TC P0=<tc-p0> P1=<tc-p1> P2=<tc-p2> P3=<tc-p3>.` Then say either `P0/P1/P2 are zero; preparing LOOP_DONE.` or `P0/P1/P2 blockers remain; another round is needed.`
   - If 0 P0/P1/P2 AND gates green: exit loop → go to step 5.
   - If `n >= <N>`: HALT per CONTRACT §8 trigger 5. Do NOT post `LOOP_DONE`. Print: "TOTAL P0=<a> P1=<b> P2=<c> P3=<d>. P0/P1/P2 blockers remain; loop cap N=<N> exhausted at HEAD `<short-sha>`."
   - Else: feed self-review findings back into Coder phase; continue.

5. Post the marker:

```
LOOP_DONE_codex-cli_<short-sha> TOTAL P0=0 P1=0 P2=0 P3=<total-p3> | CQ P0=0 P1=0 P2=0 P3=<cq-p3> | SP P0=0 P1=0 P2=0 P3=<sp-p3> | TC P0=0 P1=0 P2=0 P3=<tc-p3>

Vendor: codex-cli
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

Post via `gh pr comment <PR> --body-file <tempfile>`.

6. Print to user, deriving from existing markers plus the `LOOP_DONE` just posted: if a prior independent clean marker (either vendor) is already on this HEAD → "TOTAL P0=0 P1=0 P2=0 P3=<total-p3>. P0/P1/P2 are zero; merge gate satisfied on HEAD `<short-sha>` — two independent clean reviews. Human authorization required to merge."; otherwise → "TOTAL P0=0 P1=0 P2=0 P3=<total-p3>. P0/P1/P2 are zero; first of two independent clean reviews on HEAD `<short-sha>`. Run `/review <PR>` (or `/loop <PR>`) for the second — a different vendor if available (preferred), else this vendor again."

## Operate at maximum reasoning level. Do not auto-retry past the cap. Never post `LOOP_DONE` when findings remain.
