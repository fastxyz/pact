# Command: /review

**Signature:** `/review <PR>`
**Where it runs:** one vendor's CLI window.
**What it does:** performs ONE external multi-lane review of the PR's current HEAD. Posts either `REVIEW_CLEAN_<vendor>_<sha>` (no findings) or `REVIEW_FINDINGS_<vendor>_R<N>_<sha>` (findings). Does NOT write code.

## Step-by-step (vendor-agnostic)

1. Read `CONTRACT.md` and `roles/reviewer.md`
2. Read the PR state (same as `/code` step 2)
3. Compute this vendor's current R counter:
   - Count prior `REVIEW_FINDINGS_<this-vendor>_R*` markers on the PR
   - The next R = that count + 1
4. Run the three-lane review per `roles/reviewer.md` Responsibility 1. Lanes run in parallel if the vendor supports it.
5. If local CI did not run on this HEAD, run typecheck + lint + test locally per the project's `AGENTS.md` / `CLAUDE.md`
6. Aggregate findings into per-lane per-severity counts
7. Emit the marker:
   - **If 0 P0/P1/P2 AND gates green:** post `REVIEW_CLEAN_<vendor>_<sha>` per CONTRACT §5.5 (note: include P3 findings as advisory body)
   - **Else:** post `REVIEW_FINDINGS_<vendor>_R<N>_<sha>` per CONTRACT §5.5 (every finding line-anchored)
8. Print to the user:
   - If CLEAN: "Merge gate needs the other vendor's clean marker on HEAD `<sha>`."
   - If FINDINGS: "Findings posted. Run `/code` or `/loop <PR>` in the coder vendor's CLI to address them."

## Edge cases

- **0 P0/P1/P2 but gates fail:** do NOT post `REVIEW_CLEAN`; that would trip CONTRACT §8 escalation trigger 3. Instead, post `REVIEW_FINDINGS` with a TC P1 finding for the failing gate.
- **R counter would be ≥5:** the next post triggers CONTRACT §8 trigger 1 (escalation). Post the marker, then print the escalation notice to the user.
- **Same finding reappears for the 3rd time on the same vendor's R<N>:** trigger CONTRACT §8 trigger 2; print escalation notice after posting.
