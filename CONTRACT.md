# PACT — Agent Review Contract

**Version:** v1.0.6
**Canonical URL:** https://raw.githubusercontent.com/fastxyz/pact/v1.0.6/CONTRACT.md

This document is the canonical rule book for `fastxyz/pact`. Agents (Claude, Codex, and any future LLM) follow this contract when working on a PR governed by PACT. Projects opt in by adding a one-line pin to their `AGENTS.md` / `CLAUDE.md` (see this repo's README).

## 1. The Merge Gate (non-negotiable)

> Any PR merged in a PACT-governed project must have **P0 = P1 = P2 = 0** from independent reviews by at least two different LLM vendors, each conducted at the highest reasoning level available.

How the PR reaches that state is the author's choice. They may write the code by hand, use this repo's commands (§6), or follow their own discipline. The gate is the only non-negotiable rule.

## 2. Lanes

Every multi-lane review uses these three lanes. If the underlying agent supports parallel sub-agent dispatch, the lanes run in parallel; otherwise sequentially with explicit lane labels in the output.

| Lane | Focus |
|---|---|
| **CQ** (Code Quality) | architecture, hygiene, naming, error handling, security, dead code, complexity |
| **SP** (Spec / Product) | does the implementation match the spec; UX correctness; bug coverage |
| **TC** (Test Coverage) | regression risk, missing test paths, false-positive tests, flakiness |

## 3. Severity

| Severity | Meaning | Blocking? |
|---|---|---|
| P0 | correctness, safety, data-loss | yes |
| P1 | functional bug, UX failure | yes |
| P2 | quality issue, regression risk | yes |
| P3 | advisory, deferrable with reason | no |
| Nit | optional polish | no |

A PR is mergeable when **P0 = P1 = P2 = 0** under independent reviews by at least two different vendors.

## 4. Roles

- **Coder** — proposes code via PR commits. Detailed responsibilities: see `roles/coder.md`.
- **Reviewer** — performs the multi-lane review per §2. Detailed responsibilities: see `roles/reviewer.md`.

A single vendor's `/loop` command (§6.2) alternates these roles **internally** — its multi-agent dispatch acts as a Reviewer on code its same vendor just produced. This intra-vendor self-loop is allowed and expected — it's how a vendor reaches its own fixed point. The vendor's internal review is not the merge gate.

The **merge gate** (§1) requires two **different vendors** to each independently sign off on the same HEAD. A PR cannot merge with only one vendor's clean marker, regardless of how thorough that vendor's internal loop was.

## 5. Marker formats

Four marker types appear as PR comments. Each is a single fenced-code block at the top of the PR comment so it can be programmatically parsed.

**CODE_DONE** — posted by `/code` when the running vendor finishes a one-shot coding pass (no internal review):

```
CODE_DONE_<vendor>_<sha>

Vendor: <vendor name>
HEAD: <full commit SHA>
Responding to: <prior REVIEW_FINDINGS marker if any, or "initial implementation">
Disposition per prior finding (if responding to REVIEW_FINDINGS):
  - [<lane> <severity> #<id>]: fixed in <sha> | deferred — Why: <reason> | disputed — Counter: <argument>
  - ...
Commits pushed: <list of SHAs>
Gates: typecheck=<PASS|FAIL>, lint=<PASS|FAIL>, test=<PASS:<n>/<m>|FAIL:<n>/<m>>
CI: <link or "not yet fired">
```

`CODE_DONE` is an "I pushed code, please review" signal. It is NOT a clean marker — it does not satisfy any part of the merge gate by itself. The merge gate still requires clean reviews (`LOOP_DONE` or `REVIEW_CLEAN`) from two different vendors on the same HEAD.

The Disposition section is omitted on the initial implementation (R1) when there are no prior findings to respond to.

**LOOP_DONE** — posted by `/loop` when the running vendor's internal review reaches P0=P1=P2=0:

```
LOOP_DONE_<vendor>_<sha>

Vendor: <vendor name, e.g. claude-code, codex-cli>
HEAD: <full commit SHA>
Internal rounds taken: <how many internal code→self-review→fix cycles>
Final internal review:
  CQ: P0=0 P1=0 P2=0 P3=<w> Nit=<n>
  SP: P0=0 P1=0 P2=0 P3=<w> Nit=<n>
  TC: P0=0 P1=0 P2=0 P3=<w> Nit=<n>
Gates: typecheck=PASS, lint=PASS, test=PASS <n>/<m>
CI: <link or "not yet fired">
Commits pushed this loop: <list of SHAs>
```

**REVIEW_CLEAN** — posted by `/review` when the running vendor's external review finds zero P0/P1/P2:

```
REVIEW_CLEAN_<vendor>_<sha>

Vendor: <vendor name>
HEAD reviewed: <full commit SHA>
Existing markers on HEAD:
  - REVIEW_CLEAN_<other-vendor>_<sha>  (posted <ISO timestamp>)
  - LOOP_DONE_<other-vendor>_<sha>  (posted <ISO timestamp>)
  - ...
  (List other-vendor markers first, then same-vendor. Use "none" if no prior markers.)
Per-lane findings:
  CQ: P0=0 P1=0 P2=0 P3=<w> Nit=<n>
  SP: P0=0 P1=0 P2=0 P3=<w> Nit=<n>
  TC: P0=0 P1=0 P2=0 P3=<w> Nit=<n>
P3 findings (advisory):
  - [<lane>] file:line — <summary>
  - ...
Local gates on this HEAD: typecheck=PASS, lint=PASS, test=PASS <n>/<m>
CI status: <green|red|not fired>
```

The `Existing markers on HEAD` field is REQUIRED. Its purpose is to force the reviewer to enumerate prior markers as a precondition for posting — the closing line ("merge gate satisfied" vs "needs another vendor") MUST be derived from this field, not from a template. A `REVIEW_CLEAN` posted without enumerating existing markers is a contract violation. `/review`'s round-zero check (see `commands/review.md` step 3) uses the same enumeration to decide whether to skip the review entirely.

**REVIEW_FINDINGS** — posted by `/review` when the running vendor's external review finds at least one P0/P1/P2:

```
REVIEW_FINDINGS_<vendor>_R<N>_<sha>

Vendor: <vendor name>
Round (this vendor's nth findings post on this PR): <N>
HEAD reviewed: <full commit SHA>
Existing markers on HEAD:
  - REVIEW_CLEAN_<other-vendor>_<sha>  (posted <ISO timestamp>)
  - LOOP_DONE_<other-vendor>_<sha>  (posted <ISO timestamp>)
  - ...
  (List other-vendor markers first, then same-vendor. Use "none" if no prior markers.)
Per-lane counts:
  CQ: P0=<x> P1=<y> P2=<z> P3=<w> Nit=<n>
  SP: P0=<x> P1=<y> P2=<z> P3=<w> Nit=<n>
  TC: P0=<x> P1=<y> P2=<z> P3=<w> Nit=<n>
Findings (each line-anchored):
  - [CQ P1 #1] apps/foo/bar.ts:42 — <summary>
  - [SP P2 #1] apps/foo/baz.ts:88 — <summary>
  - ...
Local gates on this HEAD: typecheck=<PASS|FAIL>, lint=<PASS|FAIL>, test=<PASS:<n>/<m>|FAIL>
CI status: <green|red|not fired>
```

The `Existing markers on HEAD` field is REQUIRED on both `REVIEW_CLEAN` and `REVIEW_FINDINGS`. See the `REVIEW_CLEAN` schema note above for rationale: it forces the reviewer to enumerate prior markers as a precondition for posting, which both enables the round-zero check (`commands/review.md` step 3) and prevents stale "needs another vendor" closing lines when the gate is already satisfied. A non-trivial `REVIEW_FINDINGS` whose body shows a different vendor already posted a clean marker on the same HEAD is a contract-aware signal that something materially new must have changed (e.g., a regression the prior vendor missed) — surface that in the findings, don't bury it.

**Round-counter rules:** `R<N>` appears only on `REVIEW_FINDINGS`. Each vendor maintains its own R counter, incrementing only when that vendor posts a new `REVIEW_FINDINGS`. `CODE_DONE`, `LOOP_DONE`, and `REVIEW_CLEAN` do not carry R counters (they are terminal verdicts for that invocation, or in `CODE_DONE`'s case, a "your turn" signal).

**Vendor naming:** the `<vendor>` field is a stable short identifier (`claude-code`, `codex-cli`, `gpt5-cli`, `gemini-cli`, `anthropic-api`, etc.). Listed in `adapters/<vendor>/README.md` for each adapter. The merge-gate check compares vendor identifiers exactly.

**SHA in marker name:** the short HEAD SHA is appended to the marker title so a grep over PR comments can find all markers per HEAD. The body has the full SHA.

## 6. Commands

PACT v1 ships three commands. All are single-vendor: each runs entirely in one vendor's CLI and produces a marker on the PR. They do not invoke other vendors. The user manually alternates between vendor windows.

| Command | Posts marker | Per-command spec |
|---|---|---|
| `/code <PR>` | `CODE_DONE_<vendor>_<sha>` | `commands/code.md` |
| `/loop <PR> [N]` | `LOOP_DONE_<vendor>_<sha>` (default cap N=5) | `commands/loop.md` |
| `/review <PR>` | `REVIEW_CLEAN_<vendor>_<sha>` or `REVIEW_FINDINGS_<vendor>_R<N>_<sha>` | `commands/review.md` |

See each command's spec for step-by-step behavior. Vendor-specific implementations live under `adapters/<vendor>/`.

## 7. Convergence and the merge gate

**Internal (`/loop`'s fixed point):** the running vendor's own multi-lane review on the latest HEAD reports 0 P0/P1/P2, with gates green (CI green OR local gates pass on that HEAD). At this point `/loop` posts `LOOP_DONE` and exits.

**External (per-vendor fixed point via `/review`):** the running vendor's external review reports 0 P0/P1/P2 with gates green. Posts `REVIEW_CLEAN` and exits.

**Merge gate (cross-vendor):** the PR has both `LOOP_DONE_<vendor1>_<sha>` (or `REVIEW_CLEAN_<vendor1>_<sha>`) AND a `LOOP_DONE` or `REVIEW_CLEAN` from a different vendor on the SAME HEAD `<sha>`. Once both clean markers exist on the same HEAD, the PR is mergeable. Human authorization is still required (no auto-merge).

If a new commit lands after a clean marker is posted, that marker is stale for merge-gate purposes — the vendor that posted it must re-run its command on the new HEAD.

## 8. Escalation triggers

Any one of these halts the running command and notifies the human PR owner:

1. **Per-vendor R counter hits 5.** A vendor has posted 5 `REVIEW_FINDINGS` markers on this PR without ever posting `REVIEW_CLEAN` or `LOOP_DONE` on the resulting HEAD. Something structural is wrong — escalate.
2. **Same finding (matched by lane + file:line) stays open across 3 consecutive `REVIEW_FINDINGS` markers from the same vendor.** The coding vendor isn't addressing it; escalate.
3. **A vendor posted `LOOP_DONE` or `REVIEW_CLEAN` but a contemporaneous local-gate run on the same HEAD fails.** Contract violation; escalate.
4. **A vendor posted `REVIEW_CLEAN` but its own marker body shows P0/P1/P2 ≥ 1.** Self-contradiction; escalate.
5. **`/loop`'s internal round counter exceeds its configured cap** (default 5; override via `[N]` syntax — see §6). When the vendor's internal code→self-review→fix cycle exhausts the cap without reaching its internal fixed point, `/loop` halts. The latest pushed commits remain on the PR; no `LOOP_DONE` marker is posted. The user can switch to another vendor and run `/review` to see what's blocking, or `/code` in either vendor to land a manual fix.

On any escalation, the command halts, prints the trigger reason, and waits for the human to decide. No further markers are posted from that invocation.

## 9. Disagreement protocol

If the running vendor disagrees with a finding from another vendor (incorporated via the latest `REVIEW_FINDINGS` marker):

- The vendor records the dispute in the Disposition (`/code`) or per-finding section (`/loop`) of its next marker — using `disputed — Counter: <argument>` for that finding
- The disputing vendor does NOT silently ignore findings; silent ignoring is a contract violation that fails the merge gate at the human-reviewer check
- The other vendor's next `/review` reads the disputes; if convinced, the finding is omitted from the new `REVIEW_FINDINGS` marker; if not convinced, the finding reappears
- If the same finding reappears across 3 review rounds with active dispute, escalation trigger #2 fires

## 10. Trivial-nit carve-out

Either vendor may commit trivial nit fixes (typos, formatting, single-line comment clarifications) inside its `/loop` without flagging in the marker. Anything requiring design judgment must surface in the marker so the other vendor's next review sees the change.

## 11. Versioning and adoption

PACT releases are semver-tagged in `fastxyz/pact`. Projects pin a version in their `AGENTS.md` / `CLAUDE.md`:

> This project follows `fastxyz/pact` v1.x. The merge gate (§1 of the contract) applies.

Agents read this document from the pinned version's raw URL. No vendoring required.
