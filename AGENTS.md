# AGENTS.md

Roles per QUANT_RESEARCH_OS.md §11:

- Research director / spec author: ChatGPT-side conversation with Dylan
  (discussion outputs recorded in session transcripts).
- Implementation agent (this repo, branch
  `claude/reversal-continuation-research-p6hsdi`): Claude Code — Stage 0-2
  execution under SPEC_LOCKED.md. Does not silently resolve material
  research ambiguities; stops and reports.
- Independent audit agent: NOT YET RUN. Required before Stage 4 selection
  and before any holdout unlock; must work read-only from a separate
  worktree/branch and re-derive key ledgers.
- Dylan: approves material assumptions, spec amendments, stage transitions,
  holdout unlock.

Rules of engagement: raw data immutable; holdout unread; every analysis
configuration registered in RUN_REGISTRY.csv; deterministic seeds; no agent
edits another agent's workspace concurrently; disputes adjudicated by
committed artifacts and tests, not claims.
