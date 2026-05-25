# /loop — Codex CLI prompt template

Substitute `<PR>` (required) and `<N>` (optional, default 5) before pasting.

---

You are executing PACT (`fastxyz/pact`) `/loop` for PR #<PR>, with internal-rounds cap N=<N>. Vendor identifier is `codex-cli`.

## Required reading

Same as `/code` plus:
- `https://raw.githubusercontent.com/fastxyz/pact/v1.0.0/roles/reviewer.md`
- `https://raw.githubusercontent.com/fastxyz/pact/v1.0.0/commands/loop.md`

## Argument parsing

`[N]` in CONTRACT syntax is the max internal rounds (default 5). For this paste, N=<N> is already substituted.

## Execution

1. Read PR state (same as `/code` step 1).
2. Ingest the latest unresolved `REVIEW_FINDINGS` from a vendor other than `codex-cli` (if any).
3. Set internal round counter `n = 0`.
4. Enter the internal loop:
   - `n += 1`
   - **Coder phase:** implement per `roles/coder.md`. Run gates. If gates fail, HALT (do not post `LOOP_DONE`). If gates pass, push.
   - **Self-review phase:** spawn three concurrent subtasks (or run sequentially if your Codex version lacks concurrency), one per lane:
     - CQ subtask: "Review PR <PR> HEAD <sha> diff on lane CQ per fastxyz/pact roles/reviewer.md. Report `[CQ <sev>] <file:line> — <summary>` + per-severity counts. No code changes."
     - SP subtask: similar with lane SP, including the spec from PR description
     - TC subtask: similar with lane TC, may run local gates
   - Aggregate. If 0 P0/P1/P2 AND gates green: exit loop → go to step 5.
   - If `n >= <N>`: HALT per CONTRACT §8 trigger 5. Do NOT post `LOOP_DONE`. Print: "Loop cap N=<N> exhausted at HEAD `<short-sha>`. Findings remain: P0=<a> P1=<b> P2=<c>."
   - Else: feed self-review findings back into Coder phase; continue.

5. Post the marker:

```
LOOP_DONE_codex-cli_<short-sha>

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

6. Print to user: "Merge gate (CONTRACT §7) needs a clean marker from a different vendor on HEAD `<short-sha>`. Switch to another vendor's CLI and run `/review <PR>` (or `/loop <PR>`)."

## Operate at maximum reasoning level. Do not auto-retry past the cap. Never post `LOOP_DONE` when findings remain.
