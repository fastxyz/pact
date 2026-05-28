# /code — Codex CLI prompt template

Substitute `<PR>` with the actual PR number, then paste this entire prompt as your first message to Codex CLI.

---

You are executing PACT (`fastxyz/pact`) `/code` for PR #<PR>. Vendor identifier for your role here is `codex-cli`.

## Required reading (do this first)

Fetch and read these documents in order:

1. `https://raw.githubusercontent.com/fastxyz/pact/main/CONTRACT.md` — read §1, §3, §4, §5, §8 carefully
2. `https://raw.githubusercontent.com/fastxyz/pact/main/roles/coder.md`
3. `https://raw.githubusercontent.com/fastxyz/pact/main/commands/code.md`
4. The current project's `AGENTS.md` and `CLAUDE.md` from the local repo

Fetch with `curl -sL <url>` if URL access is allowed; otherwise note that the user can paste the contents.

## Execution

1. Read PR state:
   - `gh pr view <PR> --json number,headRefName,headRefOid,baseRefName,title,url`
   - `gh pr diff <PR>`
   - `gh pr view <PR> --comments` — find the latest unresolved `REVIEW_FINDINGS_*` marker authored by a vendor other than `codex-cli`
   - `gh pr checks <PR>` for CI status

2. Plan the coder pass per `roles/coder.md` Responsibility 1.

3. Implement the changes. Run gates locally (project commands from `AGENTS.md` / `CLAUDE.md`, e.g. `npm run typecheck && npm run lint && npm test`).

4. If any gate fails: STOP. Do not push. Do not post a marker. Report to the user.

5. If gates pass: `git push`. Capture the new HEAD SHA.

6. Post the marker. Build this exact body (replace placeholders):

```
CODE_DONE_codex-cli_<short-sha>

Vendor: codex-cli
HEAD: <full SHA>
Responding to: <prior REVIEW_FINDINGS marker title, or "initial implementation">
Disposition per prior finding:
  - [CQ P1 #1]: fixed in <sha> | deferred — Why: <reason> | disputed — Counter: <argument>
  - ... (omit this whole section on initial implementation)
Commits pushed: <comma-separated short SHAs>
Gates: typecheck=PASS, lint=PASS, test=PASS <n>/<m>
CI: <link or "not yet fired">
```

Post:

```
gh pr comment <PR> --body-file <tempfile>
```

7. Print to user: "Code pushed at HEAD `<short-sha>`. Switch to another vendor's CLI (e.g., Claude Code) and run `/review <PR>` to verify."

## Operate at maximum reasoning level. Address each finding deliberately — fix, defer with reason, or dispute with counter-argument. Never silently ignore.
