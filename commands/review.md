# Command: /review

**Signature:** `/review <PR>`
**Where it runs:** one vendor's CLI window.
**What it does:** performs ONE external multi-lane review of the PR's current HEAD. Posts either `REVIEW_CLEAN_<vendor>_<sha>` (no findings) or `REVIEW_FINDINGS_<vendor>_R<N>_<sha>` (findings). Does NOT write code.

## Step-by-step (vendor-agnostic)

1. Read `CONTRACT.md` and `roles/reviewer.md`
2. Read the PR state (same as `/code` step 2): HEAD SHA, full diff vs base branch, **and the full list of existing markers from ALL vendors on the current HEAD** (cross-vendor and same-vendor). The marker enumeration produced here is the value that lands in the marker body's `Existing markers on HEAD:` field (see step 8).

   This enumeration is non-optional. Without it, the closing line in step 9 cannot be derived from observed state — and a closing line emitted from a template ("needs another vendor") will silently contradict the actual gate status when a prior vendor has already cleared.

3. **Same-HEAD duplicate guard.** If a `REVIEW_CLEAN_<this-vendor>_<sha>` or `LOOP_DONE_<this-vendor>_<sha>` already exists on the current HEAD AND there are no unresolved `REVIEW_FINDINGS_*` markers, this vendor has already verified the current HEAD — re-posting would duplicate this vendor's own vote, not contribute to the merge gate. Print:

   `"This vendor already cleared HEAD <sha> at <prior marker timestamp>. Not posting a duplicate marker."`

   Then check what the broader merge-gate state is and append one of the closing-line cases from step 9. Exit.

   Note: this guard is intentionally narrow — it fires only when THIS vendor already cleared the current HEAD. A different vendor's clean marker does NOT trigger it: the merge gate (CONTRACT §1) requires both vendors, so this vendor's review is still needed to contribute the second vote even when the other vendor has cleared.

4. Compute this vendor's current R counter:
   - Count prior `REVIEW_FINDINGS_<this-vendor>_R*` markers on the PR
   - The next R = that count + 1
5. Run the three-lane review per `roles/reviewer.md` Responsibility 1. Lanes run in parallel if the vendor supports it.
6. If local CI did not run on this HEAD, run typecheck + lint + test locally per the project's `AGENTS.md` / `CLAUDE.md`
7. Aggregate findings into per-lane per-severity counts
8. Emit the marker. The marker body MUST include the `Existing markers on HEAD <sha>:` field (see CONTRACT §5) enumerating every prior marker on the current HEAD. This is a hard schema requirement, not optional: it forces the reviewer to derive the closing line from observed state rather than from a template.
   - **If 0 P0/P1/P2 AND gates green:** post `REVIEW_CLEAN_<vendor>_<sha>` per CONTRACT §5 (note: include P3 findings as advisory body)
   - **Else:** post `REVIEW_FINDINGS_<vendor>_R<N>_<sha>` per CONTRACT §5 (every finding line-anchored)
9. Print to the user — derive the closing line from the `Existing markers` field PLUS the marker just posted. Never from a template. Three cases:
   - **This marker is `REVIEW_CLEAN` AND a different-vendor `REVIEW_CLEAN`/`LOOP_DONE` is in the `Existing markers` list** → both vendors now cover the same HEAD; merge gate is satisfied:
     `"Merge gate satisfied on HEAD <sha> (this vendor + prior <other-vendor> clean marker). Human authorization required to merge."`
   - **This marker is `REVIEW_CLEAN` AND no different-vendor clean marker exists yet** → first vendor's confirmation:
     `"Merge gate needs the other vendor's clean marker on HEAD <sha>. Run /review <PR> (or /loop <PR>) from a different vendor's CLI."`
   - **This marker is `REVIEW_FINDINGS`** → coder's turn:
     `"Findings posted. Run /code or /loop <PR> in the coder vendor's CLI to address them."`

## Edge cases

- **0 P0/P1/P2 but gates fail:** do NOT post `REVIEW_CLEAN`; that would trip CONTRACT §8 escalation trigger 3. Instead, post `REVIEW_FINDINGS` with a TC P1 finding for the failing gate.
- **R counter would be ≥5:** the next post triggers CONTRACT §8 trigger 1 (escalation). Post the marker, then print the escalation notice to the user.
- **Same finding reappears for the 3rd time on the same vendor's R<N>:** trigger CONTRACT §8 trigger 2; print escalation notice after posting.
- **Same-HEAD duplicate guard fires (step 3):** the canonical "user re-invoked /review on a HEAD this vendor already cleared" path — print the duplicate notice plus the current merge-gate status, exit without posting. This is asymmetric with `/loop`'s round-zero exit on purpose: `/loop`'s round-zero exit POSTS `LOOP_DONE` (with `Internal rounds taken: 0`) because that's how a /loop invocation contributes to the merge gate even with no Coder work to do. `/review` already posted its marker on the prior invocation; re-posting would be a same-vendor duplicate, not a fresh vote.
- **Cross-vendor confirmation (different vendor already cleared, this vendor has not):** do NOT skip. Run the lanes and post normally. The closing line at step 9 will use the "merge gate satisfied" form because the `Existing markers` field will cite the prior vendor's clean marker. This is the path that actually contributes the second-vendor vote — skipping it would freeze the gate at 1/2 indefinitely.
