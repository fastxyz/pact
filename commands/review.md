# Command: /review

**Signature:** `/review <PR>`
**Where it runs:** one vendor's CLI window.
**What it does:** performs ONE external multi-lane review of the PR's current HEAD. Posts either `REVIEW_CLEAN_<vendor>_<sha>` (no findings) or `REVIEW_FINDINGS_<vendor>_R<N>_<sha>` (findings). Does NOT write code.

## Step-by-step (vendor-agnostic)

1. Read `CONTRACT.md` and `roles/reviewer.md`
2. Read the PR state (same as `/code` step 2): HEAD SHA, full diff vs base branch, **and the full list of existing markers from ALL vendors** (cross-vendor and same-vendor)
3. **Round-zero check (merge gate may already be satisfied).** If ALL of the following hold on the PR's current HEAD:
   - A `REVIEW_CLEAN_*` or `LOOP_DONE_*` marker exists from a vendor DIFFERENT from this one, AND
   - There are NO unresolved `REVIEW_FINDINGS_*` markers anywhere on the PR (cross-vendor or same-vendor)

   then the merge gate (CONTRACT §7) is ALREADY satisfied. Print to the user:

   `"Merge gate satisfied on HEAD <sha> (prior <other-vendor> clean marker covers it). Not posting a redundant marker. Human authorization required to merge."`

   and exit. Do NOT run the lane reviews. Do NOT post a marker. Do NOT run local gates.

   This mirrors the round-zero check in `/loop` (step 5 of `commands/loop.md`). A redundant marker wastes compute, adds chat noise, and risks the agent emitting a stale "needs another vendor" closing line that contradicts the already-satisfied gate.

   **Force-override:** if the user explicitly invokes `/review <PR> --cross-verify`, run the lanes anyway. The marker shape is unchanged; the closing line acknowledges the prior vendor's clean marker (see step 9 below). Use this only when the user has a substantive reason to triple-check (e.g., security-sensitive change with a prior clean from a vendor known to under-weight that lane).

4. Compute this vendor's current R counter:
   - Count prior `REVIEW_FINDINGS_<this-vendor>_R*` markers on the PR
   - The next R = that count + 1
5. Run the three-lane review per `roles/reviewer.md` Responsibility 1. Lanes run in parallel if the vendor supports it.
6. If local CI did not run on this HEAD, run typecheck + lint + test locally per the project's `AGENTS.md` / `CLAUDE.md`
7. Aggregate findings into per-lane per-severity counts
8. Emit the marker. The marker body MUST include the `Existing markers on HEAD <sha>:` field (see CONTRACT §5) enumerating every prior marker on the current HEAD. This is a hard schema requirement, not optional: it forces the reviewer to derive the closing line from observed state rather than from a template.
   - **If 0 P0/P1/P2 AND gates green:** post `REVIEW_CLEAN_<vendor>_<sha>` per CONTRACT §5 (note: include P3 findings as advisory body)
   - **Else:** post `REVIEW_FINDINGS_<vendor>_R<N>_<sha>` per CONTRACT §5 (every finding line-anchored)
9. Print to the user — derive the closing line from the `Existing markers` field, never from a template:
   - If this marker plus a different-vendor clean marker now both cover HEAD `<sha>`: `"Merge gate satisfied on HEAD <sha> (this vendor + prior <other-vendor> clean marker). Human authorization required to merge."`
   - If this is the only clean marker on HEAD (no different-vendor clean yet): `"Merge gate needs the other vendor's clean marker on HEAD <sha>. Run /review <PR> (or /loop <PR>) from a different vendor's CLI."`
   - If this is a `REVIEW_FINDINGS`: `"Findings posted. Run /code or /loop <PR> in the coder vendor's CLI to address them."`

## Edge cases

- **0 P0/P1/P2 but gates fail:** do NOT post `REVIEW_CLEAN`; that would trip CONTRACT §8 escalation trigger 3. Instead, post `REVIEW_FINDINGS` with a TC P1 finding for the failing gate.
- **R counter would be ≥5:** the next post triggers CONTRACT §8 trigger 1 (escalation). Post the marker, then print the escalation notice to the user.
- **Same finding reappears for the 3rd time on the same vendor's R<N>:** trigger CONTRACT §8 trigger 2; print escalation notice after posting.
- **Round-zero exit (gate already satisfied):** the canonical "I asked the second vendor to review and it noticed the first vendor was already done" path. Zero compute spent, no marker posted, user told the gate is met. This is the symmetric counterpart to `/loop`'s round-zero exit (see `commands/loop.md` edge cases) — `/review` is the appropriate command when the user wants a literal review with no Coder phase even allocated.
- **Round-zero check fires but user invoked `--cross-verify`:** lanes run normally. The marker body's `Existing markers on HEAD` field cites the prior vendor's clean marker; the closing line uses the "merge gate satisfied" form noting both vendors' coverage.
