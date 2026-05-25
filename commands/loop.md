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
5. **Round-zero check (nothing to address).** If ALL of the following hold:
   - The latest marker on the PR is a clean marker (`REVIEW_CLEAN_*` or `LOOP_DONE_*`) from any vendor, AND
   - There are NO unresolved `REVIEW_FINDINGS_*` markers anywhere on the PR (cross-vendor or same-vendor), AND
   - This is not the initial implementation (PR already has at least one prior coder marker)

   then SKIP the Coder phase entirely. Run only the Self-review phase on the existing HEAD. There is nothing for the Coder to do, and a speculative push would (a) waste compute, (b) stale the prior vendor's clean marker, and (c) risk introducing new bugs that vendor would then have to re-flag. The Coder role per `roles/coder.md` is explicitly bounded — it acts on findings or initial spec, not speculatively.

   - If the Self-review on the existing HEAD finds 0 P0/P1/P2 AND gates green → exit to step 7 with `Internal rounds taken: 0` in the marker body.
   - If the Self-review finds findings the prior vendor missed → the Coder phase NOW has legitimate work; continue to step 6 normally.

6. **Internal loop** (track internal round count `n`, starting at 1):
   a. **Coder phase** (per `roles/coder.md`): implement code, run gates, push. The Coder is bounded: address open findings (cross-vendor `REVIEW_FINDINGS` or same-vendor self-review findings from step 6b's previous iteration) OR implement the initial spec on R1. Never push speculative changes.
   b. **Self-review phase** (per `roles/reviewer.md`): run the three lanes on the new HEAD
   c. If 0 P0/P1/P2 AND gates green: exit the internal loop successfully → go to step 7
   d. If `n >= N` (cap exhausted): halt per CONTRACT §8 trigger 5; do NOT post `LOOP_DONE`; print halt reason to user; exit
   e. Else: increment `n`; go to (a), addressing the self-review's findings
7. Post `LOOP_DONE_<vendor>_<sha>` per CONTRACT §5.5 format:
   - Body must include: Vendor, HEAD, Internal rounds taken (the final value of `n`, or `0` if the round-zero check skipped the Coder phase), Final internal review per-lane counts, Gates, CI, Commits pushed this loop (empty list if round-zero exit).
8. Print to the user: "Merge gate (CONTRACT §7) needs a clean marker from a different vendor on HEAD `<sha>`. Switch to another vendor's CLI and run `/review <PR>` (or `/loop <PR>`)."

   If the round-zero check fired (Internal rounds taken: 0), this `/loop` invocation has effectively cross-verified the existing HEAD. If a different vendor already has a clean marker on the same HEAD, the merge gate is now satisfied — print "Merge gate satisfied on HEAD `<sha>` (this vendor + prior `<other-vendor>` clean marker). Human authorization required to merge." instead.

## Edge cases

- **N = 1:** equivalent to a stricter `/code` (one push followed by one self-review; if findings, halt). Useful when you want a single attempt + verdict.
- **Cap-exhausted halt:** the latest pushed commits remain on the PR. No `LOOP_DONE` marker is posted. The user can switch vendors and run `/review` to see what's blocking, or run `/code` to land a manual fix.
- **External findings arrive mid-loop:** the loop reads markers only at step 3 (before entering). If a cross-vendor review posts during the loop, it's picked up on the next `/loop` invocation, not mid-run.
- **Internal Reviewer finds zero issues on round 1:** loop exits with `Internal rounds taken: 1`. That's the ideal case for a /loop that addressed at least one finding.
- **Round-zero exit (nothing to address):** when step 5's round-zero check fires, the loop posts `LOOP_DONE` with `Internal rounds taken: 0` and pushes no commits. This is the correct outcome when a different vendor has already posted a clean marker on the existing HEAD AND this vendor's self-review also finds it clean — the second vendor's confirmation is genuinely cross-checking, not redoing work.
- **Cross-vendor confirmation flow:** the round-zero exit is the canonical "second vendor confirms first vendor's clean review" path. If you want the second vendor to LITERALLY just review (no Coder phase even allocated), use `/review` instead — `/loop`'s round-zero check makes the two effectively equivalent when there's nothing to do.
