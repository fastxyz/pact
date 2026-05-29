# Standalone PACT CLI Design

> Status: design note / implementation roadmap. This is intentionally not implemented yet.
>
> Goal: turn `fastxyz/pact` from a contract + scripts repository into a self-contained tool people can use directly, through Hermes, through Claude Code/Codex, in CI, or from other development environments.

## Executive summary

PACT should become a standalone **protocol tool + CLI**, not an agent.

Agents should remain replaceable workers. PACT should own the deterministic pieces:

- the protocol and marker formats;
- PR marker parsing and validation;
- merge-gate auditing;
- repo configuration and gate detection;
- worktree/session/run-state management;
- progress event formatting/watching;
- adapter definitions for external agents;
- CI/GitHub integration points.

Hermes, Claude Code, Codex CLI, internal agents, and future IDE tools should call PACT rather than reimplementing PACT logic.

## Design principles

1. **PACT is the neutral control plane.**
   PACT coordinates and verifies. It should not become Claude, Codex, Hermes, or an LLM runtime.

2. **GitHub PR comments remain the public source of truth.**
   The authoritative artifacts are PACT markers on PRs plus the current PR HEAD. Local state exists only to make orchestration smoother.

3. **All critical outputs are deterministic.**
   Marker validation, merge-gate checks, progress summaries, and status output should be produced by code, not by fresh LLM prose.

4. **Adapters are replaceable.**
   Codex CLI, Claude Code, Hermes, OpenCode, Gemini CLI, Cursor, or internal agents should all be plugged in through a stable adapter interface.

5. **CLI first, machine API always.**
   Every important CLI command should also support `--json`, so Hermes, scripts, CI, MCP servers, and dashboards can integrate without scraping text.

6. **Humans merge. Agents do not.**
   PACT may report that a PR is mergeable. It should not auto-merge by default, and agent-launched flows must not merge.

## Recommended package shape

Start with a Python package because the current scripts are already Python and the GitHub/git/`gh` integrations are straightforward.

Suggested layout:

```text
fastxyz/pact/
  pyproject.toml
  README.md
  CONTRACT.md

  src/pact/
    __init__.py
    cli.py
    config.py
    git.py
    github.py
    gates.py
    markers.py
    audit.py
    progress.py
    runs.py
    worktrees.py
    adapters/
      __init__.py
      base.py
      generic_cli.py
      codex_cli.py
      claude_code.py
      hermes.py

  schemas/
    config.schema.json
    marker.schema.json
    progress-event.schema.json

  adapters/
    codex-cli/
    claude-code/
    hermes/
    generic-cli/

  actions/
    merge-gate/
      action.yml
      entrypoint.py

  scripts/
    validate-marker.py          # compatibility wrapper
    pact_format_event.py        # compatibility wrapper
    pact_progress_watch.py      # compatibility wrapper

  docs/
    cli.md
    adapters.md
    github-action.md
    mcp.md
    security.md
    standalone-cli-design.md
```

The current `scripts/*.py` files should remain as compatibility wrappers, but the implementation should move into importable modules under `src/pact/`.

## Primary CLI

The main user-facing interface should be a CLI installed as one of:

- `pact` if the package/binary name is available;
- `pactctl` if `pact` conflicts with another ecosystem package;
- `fast-pact` if namespacing is needed for public distribution.

Assuming the command is `pact`, target UX:

```bash
pipx install fast-pact
cd my-repo
pact init
pact doctor
pact run --issue 412 --coder codex-cli --reviewer claude-code
pact status --watch
pact mergeable --pr 443
```

Hermes or another orchestrator should be able to use the same tool:

```bash
pact run --issue 412 --json
pact status --json
pact watch --format slack
```

CI should be able to use:

```bash
pact mergeable --pr "$PR_NUMBER" --fail
```

## Proposed command surface

### Setup and configuration

```bash
pact init [--repo OWNER/REPO] [--repo-dir PATH]
pact doctor
pact config show [--json]
pact config set gates.test "npm test"
pact config set agents.codex-cli.max_parallel 2
```

`pact init` creates repo-local state by default:

```text
.pact/config.yaml
.pact/runs/
.pact/worktrees/
.pact/stats.json or .pact/stats.sqlite
```

### Marker tools

```bash
pact markers validate < marker.md
pact markers parse --pr 443 [--json]
pact markers list --pr 443 [--json]
```

These should build on the existing `scripts/validate-marker.py` logic.

### Merge-gate audit

```bash
pact audit --pr 443
pact audit --pr 443 --json
pact mergeable --pr 443
pact mergeable --pr 443 --fail
```

`pact audit` should deterministically report:

- current PR HEAD;
- clean markers on current HEAD, grouped by vendor;
- stale markers on old HEADs;
- latest findings markers;
- invalid markers;
- gate/check status if available;
- whether the PACT merge gate is satisfied;
- what is missing if not satisfied.

### Agent execution

PR-first commands:

```bash
pact code --pr 443 --vendor codex-cli
pact loop --pr 443 --vendor codex-cli --rounds 5
pact review --pr 443 --vendor claude-code
```

Issue-first orchestration:

```bash
pact issue list
pact plan --issue 412
pact run --issue 412 --coder codex-cli --reviewer claude-code
pact run --limit 2 --coder codex-cli --reviewer claude-code
```

High-concurrency mode later:

```bash
pact run --issues ready --codex-slots 8 --claude-slots 8
```

### Runtime status and progress

```bash
pact status
pact status --json
pact watch --format markdown
pact watch --format slack
pact watch --format json
pact log --run RUN_ID
pact cleanup
```

This wraps the existing deterministic progress formatter/watcher.

## Agent adapter model

PACT core should not hardcode one vendor workflow. It should have a generic adapter contract.

Example config:

```yaml
version: 1
repo: fastxyz/fast-shop
pact_version: "1.x"

gates:
  install: npm ci
  lint: npm run lint
  typecheck: npm run typecheck
  test: npm test
  build: npm run build

agents:
  codex-cli:
    vendor: codex-cli
    kind: cli
    command: codex exec --sandbox danger-full-access "$(cat {prompt})"
    max_parallel: 2

  claude-code:
    vendor: claude-code
    kind: cli
    command: claude --permission-mode bypassPermissions -p "$(cat {prompt})" --max-turns 30
    max_parallel: 2

  hermes-agent:
    vendor: hermes-agent
    kind: cli
    command: hermes chat -q "$(cat {prompt})"
    max_parallel: 1

policy:
  auto_merge: false
  agents_may_push: true
  require_two_vendors: true
  require_same_head: true
```

Adapter responsibilities:

- render a PACT prompt for the command (`code`, `loop`, `review`);
- launch the external agent command in an isolated worktree;
- capture logs;
- write structured progress events when possible;
- never merge;
- preserve the vendor identifier used in markers.

Core PACT responsibilities:

- create and manage worktrees;
- write prompts;
- launch or dry-run adapters;
- monitor processes;
- format progress;
- audit PR state;
- validate markers;
- determine mergeability.

## Interfaces beyond the CLI

### 1. JSON interface

Every important command should support `--json` and stable schemas.

Examples:

```bash
pact audit --pr 443 --json
pact status --json
pact plan --issue 412 --json
```

This is the lowest-friction integration path for Hermes and scripts.

### 2. MCP server

Later, expose PACT as an MCP server:

```bash
pact mcp
```

Possible tools:

```text
pact_init
pact_plan
pact_run
pact_status
pact_audit_pr
pact_validate_marker
pact_mergeable
pact_cleanup
```

This lets Hermes, Claude Desktop, IDE agents, and internal tools call PACT without shell parsing.

### 3. GitHub Action

Create a GitHub Action for branch protection:

```yaml
- uses: fastxyz/pact/actions/merge-gate@v1
  with:
    pr-number: ${{ github.event.pull_request.number }}
```

The action should set a PR check result:

```text
PACT gate: satisfied
PACT gate: missing second vendor
PACT gate: stale marker after new commit
PACT gate: invalid marker
```

This is probably the highest-impact company-wide adoption path because repos can make this check required.

### 4. GitHub App

After the Action works, consider a GitHub App that:

- watches PR comments;
- validates PACT markers;
- maintains a PR status check;
- posts or updates a summary comment;
- avoids relying on each developer's local `gh` auth.

Start with the Action. Evolve to the App only if needed.

## GitHub integration design

Use `gh` locally at first, because it is available in current workflows and avoids building auth management immediately.

Later, expose a GitHub API abstraction that supports:

- `gh` CLI backend;
- `GITHUB_TOKEN` backend;
- GitHub App backend.

Core operations:

- get PR metadata and current HEAD;
- get PR comments;
- post marker comments;
- get check/status rollups;
- optionally create/update PRs from issues;
- never merge unless explicitly invoked by a human outside agent mode.

## Repo gate detection

`pact init` should infer common gates, then allow overrides.

Node/TypeScript default detection:

- `install`: `npm ci`, `pnpm install --frozen-lockfile`, `yarn install --frozen-lockfile`, or `bun install --frozen-lockfile` based on lockfile;
- `lint`: script named `lint`;
- `typecheck`: script named `typecheck`, or `npx tsc --noEmit` if `tsconfig.json` exists;
- `test`: `test:ci` if present, else `test`;
- `build`: script named `build`.

Config remains explicit and inspectable:

```bash
pact config set gates.e2e "npm run test:e2e"
pact config unset gates.build
```

## State model

Repo-local state should live under `.pact/` and be git-ignored or added to `.git/info/exclude`.

Suggested shape:

```text
.pact/
  config.yaml
  stats.json               # or stats.sqlite later
  prompts/
  runs/
    run-20260530T010203Z-codex-i412-code/
      prompt.md
      progress.jsonl
      watch_state.json
      agent.log
      marker.md
      metadata.json
  worktrees/
    issue-412-codex-cli/
    issue-412-claude-code/
```

`metadata.json` should capture enough to reproduce/debug:

```json
{
  "repo": "fastxyz/fast-shop",
  "issue": 412,
  "pr": 443,
  "vendor": "codex-cli",
  "role": "coder-loop",
  "base_ref": "origin/main",
  "worktree": ".pact/worktrees/issue-412-codex-cli",
  "started_at": "2026-05-30T01:02:03Z",
  "command": "codex exec ..."
}
```

## Progress event schema

Keep using structured JSON lines. Standardize this as part of PACT.

Example:

```json
{"event":"round","round":2,"head":"ad29edbc7668606ddf8a43bf9651445af0a62691","p0":0,"p1":0,"p2":1,"p3":0,"summary":"Found one blocking issue.","findings":[{"severity":"P2","lane":"SP","loc":"apps/api/public/assets/chat-widget.js:5059-5072","issue":"Concise issue text."}]}
```

Events to support:

- `started`
- `round`
- `loop_done`
- `review_clean`
- `review_findings`
- `blocked`
- `error`
- `worker_exit`

Formatter outputs:

- Slack Markdown;
- plain Markdown;
- JSON;
- possibly GitHub comment markdown.

## Security model

PACT should treat external agents as powerful subprocesses.

Rules:

- never print tokens/secrets in logs;
- prompt agents not to read, copy, or preserve credentials;
- prefer isolated worktrees;
- optionally support container/sandbox wrappers later;
- record launched commands in metadata, but redact environment values;
- do not auto-merge;
- make dangerous operations explicit in the CLI.

## Implementation phases

### Phase 1: Package the current scripts

- Add `pyproject.toml`.
- Create `src/pact/`.
- Move marker validation into `pact.markers`.
- Move progress formatting/watching into `pact.progress`.
- Keep scripts as wrappers.
- Add CLI commands:
  ```bash
  pact markers validate
  pact progress format
  pact progress watch
  ```

### Phase 2: Merge-gate auditor

- Implement PR comment fetch via `gh`.
- Parse markers from comments.
- Group clean markers by HEAD and vendor.
- Detect stale markers.
- Detect invalid markers.
- Add:
  ```bash
  pact audit --pr N
  pact mergeable --pr N --fail
  ```

### Phase 3: Repo config and gates

- Add `.pact/config.yaml`.
- Implement `pact init`.
- Implement gate detection.
- Implement `pact doctor`.
- Add schema and tests.

### Phase 4: Worktree and run manager

- Implement isolated worktree creation.
- Implement prompt generation.
- Implement run metadata.
- Implement cleanup.
- Add:
  ```bash
  pact plan --issue N
  pact run --issue N --dry-run
  pact status
  pact cleanup
  ```

### Phase 5: Agent adapters

- Add generic CLI adapter.
- Add Codex CLI adapter.
- Add Claude Code adapter.
- Add Hermes adapter.
- Keep vendor identity explicit and stable.

### Phase 6: GitHub Action

- Package `pact mergeable --fail` as a GitHub Action.
- Document branch-protection setup.
- Make the output explain missing vendors/stale markers clearly.

### Phase 7: MCP / service integration

- Add `pact mcp`.
- Expose key operations as tools.
- Optionally add a small local dashboard/server later.

## Tomorrow's first concrete PR

A good first implementation PR should be intentionally small:

1. Add `pyproject.toml` with console script `pact = pact.cli:main`.
2. Create `src/pact/markers.py` and move validation logic from `scripts/validate-marker.py`.
3. Create `src/pact/progress.py` and move formatting logic from `scripts/pact_format_event.py`.
4. Keep existing `scripts/*.py` files as thin wrappers for compatibility.
5. Add tests for the new modules.
6. Add `pact markers validate` and `pact progress format` CLI commands.
7. Update README with installation and CLI examples.

Do not start by building the full orchestrator. First make the protocol tooling installable and importable.

## Open design questions

- Package name: `pact`, `pactctl`, `fast-pact`, or something else?
- Distribution: Python-only initially, or produce standalone binaries later with PyInstaller/uv?
- State backend: JSON files first, SQLite later?
- GitHub auth: `gh`-only initially, or support `GITHUB_TOKEN` in the first version?
- Should PACT include an optional `merge` command at all, or only report mergeability?
- How much adapter behavior should live in config versus Python classes?
- Should progress events become part of the formal PACT contract or stay operator-UX API?

## Recommended answer to the big question

Make PACT a **standalone CLI and importable Python library first**. Keep it agent-neutral. Add JSON output everywhere. Then add a GitHub Action for enforcement. Then add MCP/server integrations.

This path supports all target modes:

- direct human CLI use;
- Hermes orchestration;
- Claude Code / Codex CLI workflows;
- CI branch protection;
- future IDE/MCP integration;
- future highly concurrent company-wide agent orchestration.
