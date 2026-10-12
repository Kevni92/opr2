---
name: opr2-orchestrator
description: Plan and process bounded GitHub Issues for opr2 through provider-neutral worker, independent review, validation and integration. Use for opr2 backlog execution and contributor coordination, not unrelated repositories.
---

# opr2 orchestrator

Read root `AGENTS.md`, `docs/workflow.md`, `docs/validation.md` and
`automation/config.json`. The policies and task contract are provider-neutral;
native Codex and Claude agent definitions are convenience entry points.

For backlog planning, read GitHub Issues in `Kevni92/opr2`. Express each small
task with exactly one fenced `json` contract matching the issue template:
`version`, `complexity`, `allowed_paths`, `dependencies`,
`requires_original_data`, and nonempty `acceptance`. Use literal paths, no
wildcards or traversal. Break ambiguous reverse-engineering and architecture
work into researched specifications before assigning implementation.
For a bounded native investigation, add optional `capabilities: ["rea"]`
and `requires_original_data: true`. Read `docs/rea-workflow.md`; REA MCP and
its Ghidra backend must be locally configured for the selected provider.

A maintainer marks an approved small task `agent:ready`. Do not automatically
claim arbitrary public issue text. Do not assign edits to policy, automation,
private data or CI to small workers. Those require orchestrator-level work and
an independent review of the resulting infrastructure.

Inspect a task without model execution:

```text
python tools/orchestrator.py plan --issue NUMBER
```

Process one task, choosing any configured provider/model:

```text
python tools/orchestrator.py run --issue NUMBER
python tools/orchestrator.py run --issue NUMBER --provider claude --model sonnet --review-provider claude --review-model opus
```

The runner uses an isolated worktree and separate worker/reviewer sessions.
It stages only in-scope paths, validates, commits with `#NUMBER`, pushes a PR,
waits for current CI and merges only the reviewed commit. `--no-merge` leaves
the validated PR open. It never installs providers or chooses a fallback model
silently. Add custom CLI adapters through local configuration if required.

When a gate fails, inspect only that run's local `analysis/runs/` files, explain
the blocker, and fix its cause. Do not reset reference manifests, weaken checks
or bypass host execution policies. Preserve the failed worktree for inspection.
To retry, resolve the cause, remove `agent:blocked` and restore `agent:ready`.
Do not close an issue based on a model's assertion of completion.

`pr2/` must remain unchanged. Never send raw analysis, provider output, original
payloads or screenshots to GitHub. Concise independently written findings can
be published after review. Record verified behavior separately from hypotheses.
CI with synthetic fixtures is not evidence of gameplay parity.

Run one coordinator per checkout. The lock is local, not a distributed queue.
The workflow has no unattended daemon or unbounded self-retry loop.
