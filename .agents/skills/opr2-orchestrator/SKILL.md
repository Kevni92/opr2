---
name: opr2-orchestrator
description: Coordinate bounded opr2 reconstruction Issues through documented specialist roles and the validated local runner. Use for opr2 planning and contributor coordination, not unrelated repositories.
---

# opr2 orchestration

Always read root `AGENTS.md` and the applicable sections of
`docs/reconstruction-workflow.md`. Read `docs/workflow.md` and
`docs/validation.md` when processing a runner task, `docs/rea-workflow.md` only
for an explicitly approved REA task, and `automation/config.json` only when
configuring or diagnosing provider/runner behavior. The reconstruction
workflow owns shared role, routing, evidence, and maturity rules; this skill
describes how to apply them. Native Codex and Claude definitions are entry
points, not policy.

## Route and plan

Use GPT-6 Sol for coordination and GPT-6 Luna for bounded specialist work.
Keep Sol on issue selection, dependency order, scope review, context handoff,
and integration decisions. Assign inventory, static decompilation, partitioning,
specification, C++ implementation, test authoring, review, and validation to
their matching specialist roles. Do not ask Sol to perform bulk decompilation.

For each proposed task, keep GitHub Issues canonical and include exactly one
fenced `json` version-1 task contract with only the supported fields:
`version`, `complexity`, `allowed_paths`, `dependencies`,
`requires_original_data`, and `acceptance`. Optional `capabilities` currently
supports only `['rea']`, and requires `requires_original_data: true`. Do not
add role, stage, package, budget, or parent keys to this contract.

Record planning-only routing metadata outside the JSON contract, in a two-column
Markdown table in the issue description:

| Field | Value |
|---|---|
| Stage | One pipeline stage or `bootstrap` |
| Role | Exactly one specialist role, or `maintainer` for a maintainer lane |
| Lane | `worker` or `maintainer` |
| Parent | Parent Issue number |
| Package | Stable domain package identifier |
| Budget | Maximum units, calls, and attempts with a stop limit |

This table is descriptive today; the runner does not parse or enforce it.
Keep each issue independently reviewable, with literal repository-relative
paths and observable acceptance criteria. Large or ambiguous work is research
and decomposition first. A maintainer must explicitly approve an Issue with
`agent:ready`; today an approved family or parent Issue does not authorize
children to start themselves. Each child needs its own bounded contract and
ready gate. After a grant validator is explicitly implemented and independently
reviewed, the coordinator may mark children ready only within that active,
bounded grant and its limits.

Use `opr2_inventory` to identify candidate subsystems and evidence gaps,
`opr2_decompiler` for one bounded static target investigation,
`opr2_partitioner` to split a subsystem into reviewable units,
`opr2_specifier` to write observed/inferred/unknown behavior,
`opr2_cpp` for assigned implementation paths, and `opr2_test_author` for
synthetic test cases. `opr2_reviewer` independently reviews the exact commit.
`opr2_validator` may run only the coordinator-supplied commands against the
reviewed commit after approval. Specialists return the existing
`automation/worker-result.schema.json`; reviewers return
`automation/review-result.schema.json`. Before reviewer approval, test command
strings are plans and must be reported as **NOT RUN**.

REA is permitted only for `opr2_inventory`, `opr2_decompiler`,
`opr2_partitioner`, or `opr2_specifier`, and only when the approved Issue
explicitly has `capabilities: ["rea"]` and
`requires_original_data: true`. Follow `docs/rea-workflow.md`: use the fresh
manifest-bound `pr2/PR2.exe` target, static Ghidra tools only, and the absolute
private analysis path supplied for that run. Do not annotate, mutate, execute,
or extract from the original. Unknown evidence stays unknown.

## Current runner workflow

Inspect a task without model execution:

```text
python tools/orchestrator.py plan --issue NUMBER
```

The current runner executes one generic worker and one independent reviewer:

```text
python tools/orchestrator.py run --issue NUMBER
```

It does not dispatch the specialist definitions, scan a queue, or resume a
partial run. Process issues sequentially, one coordinator per checkout. Do not
start a second worker beside the runner for the same Issue. Native specialist
definitions support explicit future/manual routing; automatic role dispatch,
queueing, and resume require separate bounded implementation Issues first.

The runner requires `agent:ready`, checks the contract and closed dependencies,
uses an isolated worktree, scopes the worker diff, commits with `#NUMBER`,
requests an independent review, and runs local validation only after approval.
It then pushes a PR and, unless `--no-merge` is used, waits for current CI and
merges only the exact reviewed, validated commit when branch protection and
all current checks pass. `--no-merge` leaves an open PR; it is not a resume
command. Never retry without resolving the blocker and restoring the required
ready state. Do not use model fallback or an unbounded retry loop.

The coordinator assigns one specialist role to each approved Issue, matching
its routing metadata and granted scope. A specialist must not delegate further.
Keep every handoff short: include the contract, literal allowed paths, base
commit, relevant files, bounded evidence, and the injected absolute private
output path when needed. Do not forward a parent transcript or raw private
evidence. The current automated runner itself uses one worker and does not
support specialist dispatch.

Small worker Issues cannot change policies, agent definitions, automation,
private paths, or CI. Infrastructure changes need a maintainer-owned bounded
Issue and independent review; do not route them through the small-worker path.
The coordinator owns GitHub task documentation and authorized integration
decisions. Normal worker Issue integration uses the validated runner only. A
`Lane: maintainer` Issue follows the explicit `Maintainer-Integration` route in
`docs/reconstruction-workflow.md`: bounded scope/base, primary Luna maintenance
editing, exact-path commit, separate Luna review before execution, post-approval
validation, then PR/CI/strict protection and pinned-head/base checks. Never use
`--admin` or bypass a gate; leave the PR open whenever evidence is missing.
This exception applies only to maintainer-owned Issues. Specialists do not
stage, commit, push, merge, or contact GitHub.

On a failed gate, inspect only that run's local `analysis/runs/` files, state
the blocker, and preserve evidence. Do not reset a reference manifest, weaken
guards, or bypass host execution policy. Raw REA output, transcripts, original
payloads, screenshots, manifests, and local validation results stay in ignored
`analysis/`; publish only concise independently written findings. `pr2/` is
read-only, and CI with synthetic fixtures does not establish playability or
parity.

Source: [Codex agent configuration and subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).
