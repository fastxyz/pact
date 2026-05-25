# Adapter: codex-cli

**Vendor identifier:** `codex-cli`

Implements PACT commands `/code`, `/loop`, `/review` as pasteable prompts for the Codex CLI (or any Codex-compatible interface that accepts a system+user prompt pair).

## Installation

Codex CLI doesn't natively support slash-skill files the way Claude Code does. The PACT codex adapter ships as three prompt templates: `code.md`, `loop.md`, `review.md`. Use them in either of two ways:

1. **Copy-paste:** open the prompt file, substitute `<PR>` and (for /loop) `<N>`, paste into Codex CLI as your first prompt.
2. **Shell wrapper (recommended):** drop a small wrapper script in your `$PATH` that takes `<PR>` (and optionally `<N>`), substitutes, and pipes the rendered prompt to `codex` (or whatever Codex CLI entry point you use). A sample wrapper is in `scripts/codex-wrap.sh` (deferred to v2; the wrapper is not part of the v1 shipped artifacts).

## Vendor-specific glue

- **Parallel lane dispatch:** Codex supports concurrent subtask delegation; the prompts instruct Codex to spawn three subtasks (one per lane) and aggregate. If a Codex version doesn't support that, the prompt instructs sequential execution with explicit lane labels.
- **PR comment posting:** all three prompts instruct Codex to use `gh pr comment <PR> --body-file <tempfile>`.
- **PR state reads:** `gh pr view`, `gh pr diff`, `gh pr checks`.
- **Gate execution:** project gate commands from the project's `AGENTS.md` / `CLAUDE.md`.

## Marker formatter

Each prompt embeds the CONTRACT §5.5 marker template verbatim. Codex fills in the placeholders.
