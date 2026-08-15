# TASK READY — CODEX-03

This file is the exact Git-visible starting marker for CODEX-03.

Codex must start only from the commit that adds this file.

Required task contract:

`governance/tasks/CODEX-TASK-03-OPIU-ERP-FORMULA-RULE-BUILDER-20260815-001.md`

Required checkout verification:

```text
git status --short --branch
git branch --show-current
git rev-parse HEAD
git log -1 --format=%H -- governance/tasks/TASK-READY-CODEX-03-20260815-001.md
```

The two SHA values must be identical before any implementation change.

Working branch:

`work/opiu-erp-formula-rule-builder-v1`

Status:

`READY_FOR_CODEX_03 / OWNER_ACCEPTED / RISK_L / DRAFT / NO_MERGE / NO_LIVE_WRITE`
