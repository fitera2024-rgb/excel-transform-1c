# Active Work

STATUS: `OWNER_GATE_ACCEPTED / CANONICAL_L_INTEGRATION_DISPATCH_READY / CONFLICTS_REQUIRE_SEMANTIC_RESOLUTION / DRAFT / NO_MERGE / NO_RELEASE / NO_LIVE_WRITE`

## Current objective

Create one canonical preview/export release candidate that combines the accepted capabilities of PR #24 and PR #25:

`prepared budgets + full BDR KPI/revenue/expenses + annual/monthly Intalev OPIU → exact ERP/tax/CFO and disclosure-group/formula-source decisions → maximum preview → OPIU Light / ОПИУ / Показатели export`

## Owner gate

Accepted on `2026-08-17`:

- PR #25 does not supersede PR #24;
- both development lines are required in the next canonical release candidate;
- ADO, ODBC, SQL/1C write and live write remain forbidden.

Authority:

- Issue `#27`;
- `governance/handoffs/HANDOFF-OWNER-GATE-CANONICAL-PREVIEW-EXPORT-20260817-001.md`.

## Exact Git authority

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Canonical branch: `integration/canonical-preview-export-v1`.
- Initial PR #25 parent: `c713cee112e4b935b3a5b2c319d23fc6cbf180cb`.
- Mandatory PR #24 parent: `77645317b673b2e57dea803410126a61cdaf6d83`.
- Common base: `b712cadba6d035108c56dcc9746ff42443c3b07c`.
- Conflict-discovery Draft PR: `#26`, merge state `dirty`.

## Active registry

- Work: `governance/tasks/WORK-CANONICAL-PREVIEW-EXPORT-20260817-001.md`.
- Codex: `governance/tasks/CODEX-TASK-CANONICAL-PREVIEW-EXPORT-INTEGRATION-20260817-001.md`.
- Coordinator QA: `governance/tasks/COORDINATOR-QA-CANONICAL-PREVIEW-EXPORT-20260817-001.md`.

## Current action

`DISPATCH_CODEX_SEMANTIC_INTEGRATION`

Codex must:

1. start from the exact contract head pinned in Issue #27;
2. create an ordinary two-parent integration preserving both exact histories;
3. resolve overlapping files field-by-field;
4. preserve all tests and business semantics from both parents;
5. synchronize Product, User Flow, Architecture, Decisions and Feature Baseline;
6. run full CI and Windows package smoke;
7. return `READY_FOR_COORDINATOR_QA_CANONICAL_INTEGRATION` with an exact handoff.

## Gates after Codex

1. independent coordinator Git/diff/test/package QA;
2. source reconciliation review;
3. Owner UX Smoke on one exact package;
4. separate explicit merge decision.

## Forbidden

- merge to `main` or release during integration;
- squash, rebase or history rewrite of the accepted parents;
- wholesale conflict resolution by unexplained `ours`/`theirs`;
- ADO, ODBC, direct SQL, 1C write or live write;
- fuzzy/contains/typo/case-only matching;
- universal Rules Engine or technical normal-user rules UI;
- real owner Excel/MXL, passwords, runtime DB or row-level financial output in Git;
- removal of either accepted parent capability without a new owner decision.
