# Command: /code

**Signature:** `/code <PR>`
**Where it runs:** one vendor's CLI window.
**What it does:** one coding pass. Reads the latest `REVIEW_FINDINGS` marker (if any) from another vendor, implements the fixes (or the initial spec on R1), pushes the commits, posts `CODE_DONE_<vendor>_<sha>`. Does NOT self-review.

## Step-by-step (vendor-agnostic)

1. Read `CONTRACT.md` (pinned URL or vendor-supplied cache) and `roles/coder.md`
2. Read the PR state:
   - `gh pr view <PR>` for HEAD SHA, branch, base
   - `gh pr diff <PR>` for the current diff
   - `gh pr view <PR> --comments` for all existing markers (cross-vendor)
   - `gh pr checks <PR>` for CI status
3. Identify the latest unresolved `REVIEW_FINDINGS` marker from a different vendor (if any). On R1 (no findings yet), the input is the PR's linked spec.
4. Plan the Coder pass per `roles/coder.md` Responsibility 1: for each open finding, decide fix / defer / dispute
5. Implement the code (one pass — do NOT re-review and fix again; that's `/loop`'s job)
6. Run gates: typecheck + lint + test (commands from the project's `AGENTS.md` / `CLAUDE.md`)
   - If any gate fails: do NOT push, do NOT post a marker, halt and report to user
7. Push commits to the PR branch
8. Post `CODE_DONE_<vendor>_<sha>` comment per CONTRACT §5.5 format:
   - Use `gh pr comment <PR> --body-file <tempfile>`
   - The marker body must include: Vendor, HEAD, Responding to, Disposition (if responding to findings), Commits pushed, Gates, CI
9. Print to the user: "Code pushed at HEAD `<sha>`. Switch to another vendor's CLI and run `/review <PR>` to verify."

## Edge cases

- **No findings to respond to (R1):** the "Responding to" field reads `initial implementation`; the Disposition section is omitted.
- **All findings deferred or disputed:** still produce a CODE_DONE marker; the disposition lines carry the rationale. The cross-vendor reviewer reads them on its next `/review`.
- **Gates fail after push:** push happened, but post no `CODE_DONE`. Report to user; user decides whether to fix locally and push again, or to `/loop` instead.
