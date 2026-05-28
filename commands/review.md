# Command: /review

**Signature:** `/review <PR>`
**Where it runs:** one vendor's CLI window.
**What it does:** performs ONE external multi-lane review of the PR's current HEAD. Posts either `REVIEW_CLEAN_<vendor>_<sha>` (no findings) or `REVIEW_FINDINGS_<vendor>_R<N>_<sha>` (findings). Does NOT write code.

## Step-by-step (vendor-agnostic)

1. Read `CONTRACT.md` and `roles/reviewer.md`
2. Read the PR state (same as `/code` step 2): HEAD SHA, full diff vs base branch, **and the full list of existing markers from ALL vendors on the current HEAD** (cross-vendor and same-vendor). The marker enumeration produced here is the value that lands in the marker body's `Existing markers on HEAD:` field (see step 8).

   This enumeration is non-optional. Without it, the closing line in step 9 cannot be derived from observed state — and a closing line emitted from a template ("needs another review") will silently contradict the actual gate status when the HEAD already carries two independent clean reviews.

3. **Gate-satisfied guard.** Enumerate the independent clean markers (`REVIEW_CLEAN_*` or `LOOP_DONE_*`, ANY vendor) on the current HEAD that have no unresolved `REVIEW_FINDINGS_*` after them. If there are already **two or more**, the merge gate (CONTRACT §1, §7) is satisfied on this HEAD — another review adds nothing. Print:

   `"TOTAL P0=0 P1=0 P2=0 P3=<prior-total-p3>. P0/P1/P2 are zero; merge gate already satisfied on HEAD <sha> by two independent clean reviews. Not posting a redundant marker. Human authorization required to merge."`

   Exit without posting.

   If there are **zero or one** clean markers on this HEAD, do NOT skip — this `/review` is needed to contribute a clean pass toward the two the gate requires. This holds even when the single existing clean marker is THIS vendor's own: a lone vendor may supply both independent passes when no second vendor is available (CONTRACT §1), so a same-vendor second `/review` here is a legitimate contribution, not a duplicate.

4. Compute this vendor's current R counter:
   - Count prior `REVIEW_FINDINGS_<this-vendor>_R*` markers on the PR
   - The next R = that count + 1
5. Run the three-lane review per `roles/reviewer.md` Responsibility 1. Lanes run in parallel if the vendor supports it.
6. If local CI did not run on this HEAD, run typecheck + lint + test locally per the project's `AGENTS.md` / `CLAUDE.md`
7. Aggregate findings into per-category/lane (CQ, SP, TC) per-severity counts, then sum CQ+SP+TC into aggregate P0/P1/P2/P3 totals.
8. Emit the marker. The marker first line MUST include aggregate P0/P1/P2/P3 totals first, then per-category/lane CQ/SP/TC P0/P1/P2/P3 counts, immediately after the marker title, e.g. `REVIEW_FINDINGS_<vendor>_R<N>_<sha> TOTAL P0=<n> P1=<n> P2=<n> P3=<n> | CQ P0=<n> P1=<n> P2=<n> P3=<n> | SP P0=<n> P1=<n> P2=<n> P3=<n> | TC P0=<n> P1=<n> P2=<n> P3=<n>`. The marker body MUST include the `Existing markers on HEAD:` field (see CONTRACT §5) enumerating every prior marker on the current HEAD. These are hard schema requirements, not optional: the first line lets humans scan severity immediately, and the existing-marker field forces the reviewer to derive the closing line from observed state rather than from a template.
   - **If 0 P0/P1/P2 AND gates green:** post `REVIEW_CLEAN_<vendor>_<sha>` per CONTRACT §5 (note: include P3 findings as advisory body)
   - **Else:** post `REVIEW_FINDINGS_<vendor>_R<N>_<sha>` per CONTRACT §5 (every finding line-anchored)
9. Print to the user — derive the closing line from the `Existing markers` field PLUS the marker just posted. Never from a template. Three cases:
   - **This marker is `REVIEW_CLEAN` AND the `Existing markers` list already holds one independent clean marker (`REVIEW_CLEAN`/`LOOP_DONE`, either vendor) on this HEAD** → two independent clean reviews now cover the HEAD; merge gate is satisfied:
     `"TOTAL P0=0 P1=0 P2=0 P3=<total-p3>. P0/P1/P2 are zero; merge gate satisfied on HEAD <sha> — two independent clean reviews (this pass + prior <marker>). Human authorization required to merge."`
   - **This marker is `REVIEW_CLEAN` AND no other clean marker exists on this HEAD yet** → first of two:
     `"TOTAL P0=0 P1=0 P2=0 P3=<total-p3>. P0/P1/P2 are zero; first of two independent clean reviews on HEAD <sha>. Run /review <PR> (or /loop <PR>) for the second — a different vendor if one is available (preferred), otherwise this vendor again."`
   - **This marker is `REVIEW_FINDINGS`** → coder's turn:
     `"TOTAL P0=<total-p0> P1=<total-p1> P2=<total-p2> P3=<total-p3>. P0/P1/P2 blockers remain; findings posted. Run /code or /loop <PR> to address them (any vendor — the coder's identity doesn't matter)."`

## Edge cases

- **0 P0/P1/P2 but gates fail:** do NOT post `REVIEW_CLEAN`; that would trip CONTRACT §8 escalation trigger 3. Instead, post `REVIEW_FINDINGS` with a TC P1 finding for the failing gate.
- **R counter would be ≥5:** the next post triggers CONTRACT §8 trigger 1 (escalation). Post the marker, then print the escalation notice to the user.
- **Same finding reappears for the 3rd time on the same vendor's R<N>:** trigger CONTRACT §8 trigger 2; print escalation notice after posting.
- **Gate-satisfied guard fires (step 3):** the HEAD already carries two independent clean reviews — print the satisfied notice with the first paragraph starting `TOTAL P0=0 P1=0 P2=0 P3=<prior-total-p3>. P0/P1/P2 are zero;`, exit without posting a third. A HEAD with only ONE clean marker does NOT trip this guard, even when that marker is this vendor's own — the gate needs two, and a lone vendor may supply both (CONTRACT §1).
- **Second clean pass (one clean marker already on HEAD, gate at 1/2):** do NOT skip. Run the lanes and post normally — this is the pass that closes the gate. The step 9 closing line uses the "merge gate satisfied" form because the `Existing markers` field cites the prior clean marker. This holds whether the prior marker is a different vendor's (the preferred cross-vendor path) or this vendor's own (the single-vendor fallback); skipping would freeze the gate at 1/2 indefinitely.
