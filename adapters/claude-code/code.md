---
name: code
description: PACT /code — single coder pass on a PR. Reads latest REVIEW_FINDINGS, implements fixes, pushes, posts CODE_DONE marker. Does not self-review.
---

# /code <PR>

You are running the PACT `/code` command (see `commands/code.md` in `fastxyz/pact`). Vendor identifier is `claude-code`.

## Required reading (in order)

1. `https://raw.githubusercontent.com/fastxyz/pact/v1.0.7/CONTRACT.md` — fetch with `Bash` (`curl -sL <url>`); read §1, §3, §4, §5, §8 carefully
2. `https://raw.githubusercontent.com/fastxyz/pact/v1.0.7/roles/coder.md` — fetch similarly
3. `https://raw.githubusercontent.com/fastxyz/pact/v1.0.7/commands/code.md` — fetch similarly
4. The current project's `AGENTS.md` and `CLAUDE.md` — for gate commands and project conventions

If a project pins a different PACT version (its `AGENTS.md` says `follows fastxyz/pact v1.x` with a specific version), substitute that version in the URLs above.

## Execution

1. Read PR state:
   - `gh pr view <PR> --json number,headRefName,headRefOid,baseRefName,title,url`
   - `gh pr diff <PR>`
   - `gh pr view <PR> --comments` (find the latest unresolved `REVIEW_FINDINGS_*` marker from a vendor other than `claude-code`)
   - `gh pr checks <PR>` for CI status

2. Plan the coder pass per `roles/coder.md` Responsibility 1.

3. Implement the changes using `Edit` / `Write`. Run gates via `Bash` (e.g., `npm run typecheck && npm run lint && npm test` for Node projects; the project's `AGENTS.md` is authoritative).

4. If any gate fails: STOP. Do not push. Report to the user; do not post a marker.

5. If gates pass: push via `Bash` (`git push`). Capture the new HEAD SHA.

6. Post the marker. Use this exact template, filling in the placeholders:

```
CODE_DONE_claude-code_<short-sha>

Vendor: claude-code
HEAD: <full SHA>
Responding to: <prior REVIEW_FINDINGS marker title, or "initial implementation">
Disposition per prior finding:
  - [CQ P1 #1]: fixed in <sha> | deferred — Why: <reason> | disputed — Counter: <argument>
  - ... (one line per prior finding; omit this whole section on initial implementation)
Commits pushed: <comma-separated short SHAs>
Gates: typecheck=PASS, lint=PASS, test=PASS <n>/<m>
CI: <link or "not yet fired">
```

Post via `Bash`:

```
gh pr comment <PR> --body-file <tempfile>
```

7. Print to the user (this is the visible output, not a marker): "Code pushed at HEAD `<short-sha>`. Switch to another vendor's CLI (e.g., Codex) and run `/review <PR>` to verify."

## Escalation

If the gate fails repeatedly (same gate failing across 3 attempted invocations within the same session), surface this to the user; do not loop silently.
