# Active Work

STATUS: `OWNER_GATE_ACCEPTED / SEMANTIC_TWO-PARENT_INTEGRATION_IMPLEMENTED / LOCAL_REGRESSION_GREEN / EXACT_HEAD_CI_PENDING / DRAFT / NO_MERGE / NO_RELEASE / NO_LIVE_WRITE`

## Current objective

Produce one canonical preview/export release candidate combining PR #24 and PR #25:

`prepared budgets + full BDR KPI/revenue/expenses + annual/monthly Intalev OPIU → exact ERP/tax/CFO and disclosure-group/formula-source decisions → maximum preview → OPIU Light / ОПИУ / Показатели export`

## Owner gate

Accepted on `2026-08-17`:

- PR #25 does not supersede PR #24;
- both development lines are required;
- ADO, ODBC, SQL/1C write and live write remain forbidden.

Authority:

- Issue `#27`;
- Draft PR `#28`;
- `governance/handoffs/HANDOFF-OWNER-GATE-CANONICAL-PREVIEW-EXPORT-20260817-001.md`.

## Exact Git authority

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Canonical branch: `integration/canonical-preview-export-v1`.
- Exact contract head before integration: `ab4513ed6923f56a8e8ee6dd36cfbf0e8ff04465`.
- Mandatory PR #25 ancestor: `c713cee112e4b935b3a5b2c319d23fc6cbf180cb`.
- Mandatory PR #24 parent/ancestor: `77645317b673b2e57dea803410126a61cdaf6d83`.
- Common base: `b712cadba6d035108c56dcc9746ff42443c3b07c`.
- Conflict-discovery Draft PR: `#26`.

## Integration result before exact-head CI

The ordinary merge exposed seven conflicts. They were resolved semantically, not by unexplained whole-file `ours`/`theirs`:

- governance state;
- user package documentation;
- Excel export aliases;
- application workflow and indicator precedence;
- UI context and combined business presentation;
- run-page diagnostics;
- combined indicator tests.

Preserved together:

- PR #25 full BDR, KPI, revenue, expense, saved-value, source identity, reconciliation and long-path package behavior;
- PR #24 exact OPIU formula/analytics/MXL catalog, disclosure-group resolver, fail-closed unsupported clauses, persistence and unresolved business UX;
- legacy classifier only as exact fallback when formula/source authority is absent;
- direct KPI and exact revenue/quantity resolvers;
- three-sheet export.

Codex Cloud did not start because the repository has no configured Codex environment. The coordinator continued in a controlled merge worktree and GitHub Actions diagnostic environment; the same Git-visible contracts and independent QA gate remain binding.

## Local verification completed

- compileall: PASS;
- JavaScript syntax: PASS;
- diff hygiene: PASS;
- unit without the environment-only `xlwt` case: `119 passed`;
- integration without the environment-only legacy-XLS case: `65 passed, 2 skipped`;
- UI: `35 passed`;
- combined local regression: `219 passed, 2 skipped`;
- canonical focused indicator integration: PASS.

The two omitted local cases require `xlwt`, which is installed by the canonical GitHub Python 3.11 workflow. GitHub CI is the exact-head authority.

## Current action

`PUBLISH_TWO_PARENT_MERGE_AND_RUN_CANONICAL_CI`

Canonical workflow:

`.github/workflows/canonical-preview-export.yml`

It must verify:

1. both mandatory ancestors;
2. full unit/integration/UI/full regression under Python 3.11;
3. wheel resources from both parent lines;
4. no tracked Excel/MXL owner files;
5. Windows offline package, long-path launcher, HTTP flow, legacy exact fallback, formula/source override, restart and stop;
6. ZIP integrity and SHA-256 artifact.

## Gates after CI

1. create exact integration handoff;
2. independent coordinator Git/diff/test/package QA;
3. source reconciliation review;
4. Owner UX Smoke on one exact package;
5. separate explicit merge decision.

## Forbidden

- merge to `main` or release during integration;
- squash, rebase or history rewrite of the accepted parents;
- wholesale conflict resolution by unexplained `ours`/`theirs`;
- ADO, ODBC, direct SQL, 1C write or live write;
- fuzzy/contains/typo/case-only matching;
- universal Rules Engine or technical normal-user rules UI;
- real owner Excel/MXL, passwords, runtime DB or row-level financial output in Git;
- removal of either accepted parent capability without a new owner decision.
