# Adapter: claude-code

**Vendor identifier:** `claude-code`

Implements PACT commands `/code`, `/loop`, `/review` as skills runnable inside the Claude Code CLI (https://docs.anthropic.com/claude-code).

## Installation

Copy the three skill files in this directory into your Claude Code skills directory:

```
cp adapters/claude-code/{code,loop,review}.md ~/.claude/skills/
```

After copying, restart Claude Code or invoke `/skills:reload`. The skills appear as `/code`, `/loop`, `/review`.

## Vendor-specific glue

- **Parallel lane dispatch:** uses the `Agent` tool with `subagent_type="Explore"` for read-only lanes (CQ, SP) and `general-purpose` for any lane that runs local gates (TC). All three are dispatched in one message for parallel execution.
- **PR comment posting:** uses the `Bash` tool with `gh pr comment <PR> --body-file <tempfile>`.
- **PR state reads:** uses `Bash` with `gh pr view`, `gh pr diff`, `gh pr checks`.
- **Gate execution:** the project's `AGENTS.md` / `CLAUDE.md` lists the gate commands (e.g., `npm run typecheck && npm run lint && npm test` for fast-shop). The adapter reads those and runs via `Bash`.

## Marker formatter

The three skills share a small embedded helper (inlined per skill, since Claude Code skills cannot share imports) that formats a marker body per CONTRACT §5.5. This helper appears as a fenced template in each skill file.
