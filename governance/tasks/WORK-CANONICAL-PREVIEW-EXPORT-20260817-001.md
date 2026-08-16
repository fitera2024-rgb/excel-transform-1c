# WORK — Canonical Preview/Export Integration

WORK-ID: `WORK-CANONICAL-PREVIEW-EXPORT-20260817-001`

STATUS: `OWNER_ACCEPTED / CONTRACT_IN_PREPARATION / L / NO_MERGE / NO_RELEASE / NO_LIVE_WRITE`

## Business goal

Produce one canonical preview/export release candidate that preserves the accepted capabilities of PR #24 and PR #25 without introducing any live-write path.

## Accepted release scope

- prepared budget workbooks;
- full BDR: KPI, revenue and expenses;
- annual and one-month Intalev OPIU;
- exact ERP, tax and CFO decisions;
- exact disclosure-group/formula/source OPIU resolver;
- maximum-completeness preview and attention registry;
- three-sheet XLSX export: `OPIU Light / ОПИУ / Показатели`;
- local persistence and Windows offline package;
- no ADO, ODBC, SQL/1C write or live write.

## Git authority

- Issue: `#27`.
- Integration branch: `integration/canonical-preview-export-v1`.
- Parent A: PR #25 current head `c713cee112e4b935b3a5b2c319d23fc6cbf180cb`.
- Parent B: PR #24 head `77645317b673b2e57dea803410126a61cdaf6d83`.
- Conflict-discovery Draft PR: `#26`.
- Canonical Draft PR: to be opened from the integration branch.

## Delivery sequence

1. Pin the exact contract head.
2. Codex performs the semantic two-parent integration.
3. Codex updates Product Contract, User Flow, Architecture and governance.
4. Codex runs focused and full automated verification and produces a handoff.
5. Coordinator independently reviews Git history, conflicts, diff, tests, CI and package.
6. Owner performs UX Smoke on one exact package.
7. Merge remains a separate explicit decision.

## Risk controls

Because this is risk `L`, the integration must not:

- silently drop either parent capability;
- alter financial semantics merely to make tests pass;
- guess ambiguous formulas, indicators, channels, ERP identities or organizational context;
- add a universal Rules Engine;
- add ADO or any write path;
- include real owner workbooks, MXL, passwords, runtime databases or row-level financial results in Git.

## Completion conditions

- one exact canonical head contains both mandatory parent SHAs in ancestry;
- all focused tests from both streams and full regression pass;
- package workflow passes on the exact head;
- governance describes the actual product;
- coordinator result is `READY_FOR_OWNER_UX_SMOKE`;
- owner explicitly accepts before merge.
