# opr2 development rules

These rules apply to every contributor and every AI provider. Read
`docs/workflow.md` and `docs/validation.md` when they are available.

- Implement a modern independent C++20/CMake game for Windows and Linux.
  The current bootstrap is not a playable game. Do not claim unverified parity.
- `pr2/` is the developer's fresh GOG Port Royale 2 installation. NEVER write,
  patch, delete, rename or execute anything there. Do not use the older external
  installation or its Ghidra/reimplementation project.
- All raw REA/Ghidra output, extracted data, screenshots, reference manifests,
  provider transcripts and local validation results belong under root
  `analysis/` (ignored). Never publish these through commits, Issues, PRs,
  Actions logs or artifacts. Publish only concise independently written findings.
- Never commit original binaries, DLLs, assets, scripts, fonts, manuals,
  savegames or extracted/converted copies. Tests in Git use original synthetic
  data authored for the test. `.gitignore` alone is not a security boundary.
- Work from a GitHub Issue with a bounded scope and acceptance criteria.
  Commit messages for issue work start with `#<number> `.
- Delegated workers edit only their assigned paths, do not delegate further,
  and do not commit, push, merge, change issue state or run original programs.
  The orchestrator owns these integration actions after validation.
  Workers describe tests but do not execute changed project code or build/test
  scripts before the independent review. The runner executes them after approval.
- REA analysis tasks explicitly request `capabilities: ["rea"]`. Read
  `docs/rea-workflow.md`; use the fresh manifest-bound target, static tools only,
  and the absolute private analysis output path supplied by the orchestrator.
- Provider and model are configuration choices. The user explicitly selected
  GPT-6 Sol for economical Codex coordination. Workers and independent reviewers
  default to GPT-6 Luna; Sol does not perform bulk analysis or implementation.
  Do not select another more expensive model without the user's explicit choice.
  Claude Code and other adapters
  follow the same task contract; a provider failure never triggers a fallback.
- A separate reviewer must approve the current commit. Merge requires the
  current commit's successful CI, local validation and original-data integrity
  evidence when applicable. Failed or stale evidence blocks integration.
- Never weaken guards or tests to make a task pass. Report blocking evidence.
- Runtime packages contain only project-built files and our instructions.
  Users supply original game data separately. No original DLL may be required
  by the finished Linux/Windows implementation.
- No project code license has been selected yet. Do not add one implicitly.
- Follow `docs/reconstruction-workflow.md` for package stages, role routing,
  bounded execution and evidence handoffs. GitHub Issues are the canonical
  package documentation. `automation/workflow.json` specifies planned features;
  it does not add queue, resume or specialist dispatch to the current runner.
- A planning request does not authorize running the planned packages. Preserve
  `agent:ready` and maintainer-only infrastructure boundaries. A future bounded
  family grant may authorize children only after its validator is implemented
  and independently reviewed; a model cannot grant itself additional scope.
