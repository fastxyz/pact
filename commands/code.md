# Command: /code

**Signature:** `/code <PR>`
**Where it runs:** one vendor's CLI window.
**What it does:** one coding pass. Reads the latest unresolved `REVIEW_FINDINGS` marker on the PR (from **any vendor — different OR same**), implements the fixes (or the initial spec on R1), pushes the commits, posts `CODE_DONE_<vendor>_<sha>`. Does NOT self-review.

The "any vendor" wording matters: `/code` is not restricted to cross-vendor handoff. A user can manually compose `/loop` as alternating `/review` + `/code` in the same vendor's window, addressing findings from that same vendor's prior `/review`. The cross-vendor merge gate (CONTRACT §6) is enforced by requiring two clean markers on the same HEAD — it does not constrain who finds what during the path to that gate. Either vendor may code a given PR, in any order — see CONTRACT §4 ("roles are activities, not vendor assignments").

## Workspace

Run in an **isolated git worktree** bound to this PR's branch (CONTRACT §4a) — never a directory shared with another PR or another running session. Before implementing, `git fetch` and fast-forward to the PR branch's latest pushed HEAD so you don't clobber commits the other vendor (or an earlier session) pushed; push when the pass finishes.

## Step-by-step (vendor-agnostic)

1. Read `CONTRACT.md` (pinned URL or vendor-supplied cache) and `roles/coder.md`
2. Read the PR state:
   - `gh pr view <PR>` for HEAD SHA, branch, base
   - `gh pr diff <PR>` for the current diff
   - `gh pr view <PR> --comments` for all existing markers (cross-vendor and same-vendor)
   - `gh pr checks <PR>` for CI status
3. Identify the latest unresolved `REVIEW_FINDINGS` marker on the PR. Source vendor does NOT matter — could be a different vendor's review (typical cross-vendor handoff) or the same vendor's prior `/review` (when the user is manually composing `/loop` as alternating commands in one window). On R1 (no findings yet), the input is the PR's linked spec.
4. Plan the Coder pass per `roles/coder.md` Responsibility 1: for each open finding, decide fix / defer / dispute
5. Implement the code (one pass — do NOT re-review and fix again; that's `/loop`'s job)
6. Run gates: typecheck + lint + test (commands from the project's `AGENTS.md` / `CLAUDE.md`)
   - If any gate fails: do NOT push, do NOT post a marker, halt and report to user
7. Push commits to the PR branch
8. Post `CODE_DONE_<vendor>_<sha>` comment per CONTRACT §5.5 format:
   - Use `gh pr comment <PR> --body-file <tempfile>`
   - The marker body must include: Vendor, HEAD, Responding to, Disposition (if responding to findings), Commits pushed, Gates, CI
9. Print to the user: "Code pushed at HEAD `<sha>`. Switch to another vendor's CLI and run `/review <PR>` to verify." (Note: if you're composing `/loop` manually, you may instead re-run `/review` in this same vendor's window — but the merge gate still needs a second vendor's clean marker before merge.)

## Edge cases

- **No findings to respond to (R1):** the "Responding to" field reads `initial implementation`; the Disposition section is omitted.
- **All findings deferred or disputed:** still produce a CODE_DONE marker; the disposition lines carry the rationale. The reviewer (any vendor) reads them on its next `/review`.
- **Gates fail after push:** push happened, but post no `CODE_DONE`. Report to user; user decides whether to fix locally and push again, or to `/loop` instead.
- **Responding to same-vendor findings:** valid use case. The user has manually invoked `/review` then `/code` in the same vendor's window (typically to refine before cross-vendor review, or to converge after the cross-vendor review came back CLEAN but the same-vendor review had findings). The CODE_DONE marker's "Responding to" field cites the same-vendor REVIEW_FINDINGS marker honestly.
