# Command: /loop

**Signature:** `/loop <PR> [N]`
**Where it runs:** one vendor's CLI window.
**What it does:** drives the running vendor's internal code ↔ self-review ↔ fix cycle, up to N internal rounds (default 5), until the vendor's own multi-lane review reports P0=P1=P2=0 at HEAD. Then posts `LOOP_DONE_<vendor>_<sha>`.

**Equivalence to manual composition.** `/loop` is the automated form of alternating `/review` and `/code` in the same vendor's window. A user can always manually compose the same outcome: run `/review`, then `/code` to address the same-vendor findings, then `/review` again, repeat until clean. The automated `/loop` and the manual composition produce semantically equivalent results — the difference is operational convenience, not contract semantics.

## Syntax for `[N]`

The optional `[N]` is the max-internal-rounds cap, in square brackets. Default 5. Either position accepted:
- `/loop 282` → cap 5
- `/loop 282 [10]` → cap 10
- `/loop [10] 282` → cap 10

The adapter is responsible for parsing both orders.

## Step-by-step (vendor-agnostic)

1. Read `CONTRACT.md`, `roles/coder.md`, `roles/reviewer.md`
2. Parse `[N]` from args; default 5 if absent
3. Read the PR state (same as `/code` step 2)
4. If the latest unresolved `REVIEW_FINDINGS` marker is from ANY vendor (different OR same): ingest those findings — the Coder phase must address them. The cross-vendor merge gate (§6) is enforced at the gate, not at the source of findings.
5. Enter the internal loop (track internal round count `n`, starting at 1):
   a. **Coder phase** (per `roles/coder.md`): implement code, run gates, push
   b. **Self-review phase** (per `roles/reviewer.md`): run the three lanes on the new HEAD
   c. If 0 P0/P1/P2 AND gates green: exit the internal loop successfully → go to step 6
   d. If `n >= N` (cap exhausted): halt per CONTRACT §8 trigger 5; do NOT post `LOOP_DONE`; print halt reason to user; exit
   e. Else: increment `n`; go to (a), addressing the self-review's findings
6. Post `LOOP_DONE_<vendor>_<sha>` per CONTRACT §5.5 format:
   - Body must include: Vendor, HEAD, Internal rounds taken (the final value of `n`), Final internal review per-lane counts, Gates, CI, Commits pushed this loop
7. Print to the user: "Merge gate (CONTRACT §7) needs a clean marker from a different vendor on HEAD `<sha>`. Switch to another vendor's CLI and run `/review <PR>` (or `/loop <PR>`)."

## Edge cases

- **N = 1:** equivalent to a stricter `/code` (one push followed by one self-review; if findings, halt). Useful when you want a single attempt + verdict.
- **Cap-exhausted halt:** the latest pushed commits remain on the PR. No `LOOP_DONE` marker is posted. The user can switch vendors and run `/review` to see what's blocking, or run `/code` to land a manual fix.
- **External findings arrive mid-loop:** the loop reads markers only at step 3 (before entering). If a cross-vendor review posts during the loop, it's picked up on the next `/loop` invocation, not mid-run.
- **Internal Reviewer finds zero issues on round 1:** loop exits with `Internal rounds taken: 1`. That's the ideal case.
