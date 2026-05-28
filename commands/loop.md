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
4. If the latest unresolved `REVIEW_FINDINGS` marker is from ANY vendor (different OR same): ingest those findings — the Coder phase must address them. The merge gate (§1, §7) is enforced at the gate, not at the source of findings.
5. **Round-zero check (nothing to address).** If ALL of the following hold:
   - The latest marker on the PR is a clean marker (`REVIEW_CLEAN_*` or `LOOP_DONE_*`) from any vendor, AND
   - There are NO unresolved `REVIEW_FINDINGS_*` markers anywhere on the PR (cross-vendor or same-vendor), AND
   - This is not the initial implementation (PR already has at least one prior coder marker)

   then SKIP the Coder phase entirely. Run only the Self-review phase on the existing HEAD. There is nothing for the Coder to do, and a speculative push would (a) waste compute, (b) stale the prior vendor's clean marker, and (c) risk introducing new bugs that vendor would then have to re-flag. The Coder role per `roles/coder.md` is explicitly bounded — it acts on findings or initial spec, not speculatively.

   - If the Self-review on the existing HEAD finds 0 P0/P1/P2 AND gates green → exit to step 7 with `Internal rounds taken: 0` in the marker body.
   - If the Self-review finds findings the prior vendor missed → the Coder phase NOW has legitimate work; continue to step 6 normally.

6. **Internal loop** (track internal round count `n`, starting at 1):
   a. **Round-start user status.** Before coding, print the human-facing blocker count for this round, not implementation trivia:
      `TOTAL P0=<a> P1=<b> P2=<c> P3=<d>. Round <n> starting: remaining review counts | CQ P0=<cq-p0> P1=<cq-p1> P2=<cq-p2> P3=<cq-p3> | SP P0=<sp-p0> P1=<sp-p1> P2=<sp-p2> P3=<sp-p3> | TC P0=<tc-p0> P1=<tc-p1> P2=<tc-p2> P3=<tc-p3>.`
      For round 1, these counts come from the ingested unresolved findings (or `0/0/0/0` if this is initial implementation). For later rounds, they come from the prior self-review.
   b. **Coder phase** (per `roles/coder.md`): implement code, run gates, push. The Coder is bounded: address open findings (cross-vendor `REVIEW_FINDINGS` or same-vendor self-review findings from step 6c's previous iteration) OR implement the initial spec on R1. Never push speculative changes.
   c. **Self-review phase** (per `roles/reviewer.md`): run the three lanes on the new HEAD
   d. **Round-finished user status.** Immediately after aggregating self-review, print:
      `TOTAL P0=<a> P1=<b> P2=<c> P3=<d>. Round <n> finished: remaining review counts | CQ P0=<cq-p0> P1=<cq-p1> P2=<cq-p2> P3=<cq-p3> | SP P0=<sp-p0> P1=<sp-p1> P2=<sp-p2> P3=<sp-p3> | TC P0=<tc-p0> P1=<tc-p1> P2=<tc-p2> P3=<tc-p3>.`
      Follow with one sentence: either `P0/P1/P2 are zero; preparing LOOP_DONE.` or `P0/P1/P2 blockers remain; another round is needed.`
   e. If 0 P0/P1/P2 AND gates green: exit the internal loop successfully → go to step 7
   f. If `n >= N` (cap exhausted): halt per CONTRACT §8 trigger 5; do NOT post `LOOP_DONE`; print `TOTAL P0=<a> P1=<b> P2=<c> P3=<d>. P0/P1/P2 blockers remain; loop cap N=<N> exhausted at HEAD <sha>.` before any other halt detail; exit
   g. Else: increment `n`; go to (a), addressing the self-review's findings
7. Post `LOOP_DONE_<vendor>_<sha> TOTAL P0=0 P1=0 P2=0 P3=<total-p3> | ...` per CONTRACT §5.5 format:
   - First line must include aggregate and per-lane P0/P1/P2/P3 totals.
   - Body must include: Vendor, HEAD, Internal rounds taken (the final value of `n`, or `0` if the round-zero check skipped the Coder phase), Final internal review per-lane counts, Gates, CI, Commits pushed this loop (empty list if round-zero exit).
8. Print to the user — derive the closing line from the existing markers on this HEAD plus the `LOOP_DONE` just posted (never from a template):
   - **A prior independent clean marker (`REVIEW_CLEAN`/`LOOP_DONE`, either vendor) already exists on this HEAD** → two independent clean reviews now cover it; merge gate satisfied:
     "TOTAL P0=0 P1=0 P2=0 P3=<total-p3>. P0/P1/P2 are zero; merge gate satisfied on HEAD `<sha>` — two independent clean reviews (this loop + prior `<marker>`). Human authorization required to merge."
   - **No other clean marker on this HEAD yet** → first of two:
     "TOTAL P0=0 P1=0 P2=0 P3=<total-p3>. P0/P1/P2 are zero; first of two independent clean reviews on HEAD `<sha>`. Run `/review <PR>` (or `/loop <PR>`) for the second — a different vendor if available (preferred), otherwise this vendor again."

## Edge cases

- **N = 1:** equivalent to a stricter `/code` (one push followed by one self-review; if findings, halt). Useful when you want a single attempt + verdict.
- **Cap-exhausted halt:** the first paragraph MUST start with `TOTAL P0=<a> P1=<b> P2=<c> P3=<d>.` and state that blockers remain before explaining the cap. The latest pushed commits remain on the PR. No `LOOP_DONE` marker is posted. The user can switch vendors and run `/review` to see what's blocking, or run `/code` to land a manual fix.
- **External findings arrive mid-loop:** the loop reads markers only at step 3 (before entering). If a cross-vendor review posts during the loop, it's picked up on the next `/loop` invocation, not mid-run.
- **Internal Reviewer finds zero issues on round 1:** loop exits with `Internal rounds taken: 1`. That's the ideal case for a /loop that addressed at least one finding.
- **Round-zero exit (nothing to address):** when step 5's round-zero check fires, the loop posts `LOOP_DONE` with `Internal rounds taken: 0` and pushes no commits. This is the correct outcome when a clean marker already exists on the HEAD AND this loop's self-review also finds it clean — a genuine independent confirmation, not redone work. If that prior marker was a different vendor's, this is the canonical cross-vendor confirmation that closes the gate.
- **Second-pass confirmation flow:** the round-zero exit is the canonical "second independent pass confirms the first clean review" path (cross-vendor when a second vendor is available, same-vendor as the fallback). If you want a pass that LITERALLY just reviews (no Coder phase even allocated), use `/review` instead — `/loop`'s round-zero check makes the two effectively equivalent when there's nothing to do.
