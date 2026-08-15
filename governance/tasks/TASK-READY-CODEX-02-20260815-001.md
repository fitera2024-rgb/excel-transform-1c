# TASK READY — CODEX-02

This file is the exact Git-visible starting marker for CODEX-02.

Codex must start only from the commit that adds this file.

Required task contract:

`governance/tasks/CODEX-TASK-02-CANONICAL-MERGE-INDICATOR-QA-20260815-001.md`

Required verification:

```text
git rev-parse HEAD
git log -1 --format=%H -- governance/tasks/TASK-READY-CODEX-02-20260815-001.md
```

The two SHAs must be identical before any implementation change.

Status:

`READY_FOR_CODEX_02 / DRAFT / NO_MERGE / NO_LIVE_WRITE`
