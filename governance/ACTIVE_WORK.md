# Active Work

STATUS: `CANONICAL_TWO-PARENT_INTEGRATION_IMPLEMENTED / EXACT_HEAD_CI_GREEN / WINDOWS_PACKAGE_GREEN / READY_FOR_COORDINATOR_QA / DRAFT / NO_MERGE / NO_RELEASE / NO_LIVE_WRITE`

## Current objective

One canonical preview/export release candidate now combines PR #24 and PR #25:

`prepared budgets + full BDR KPI/revenue/expenses + annual/monthly Intalev OPIU → exact ERP/tax/CFO and disclosure-group/formula-source decisions → maximum preview → OPIU Light / ОПИУ / Показатели export`

## Owner gate

Accepted on `2026-08-17`:

- PR #25 does not supersede PR #24;
- both development lines are required;
- ADO, ODBC, SQL/1C write and live write remain forbidden.

Authority:

- Issue `#27`;
- canonical Draft PR `#28`;
- `governance/handoffs/HANDOFF-OWNER-GATE-CANONICAL-PREVIEW-EXPORT-20260817-001.md`.

## Exact Git authority

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Canonical branch: `integration/canonical-preview-export-v1`.
- Exact contract head before integration: `ab4513ed6923f56a8e8ee6dd36cfbf0e8ff04465`.
- Exact two-parent code merge: `b5bf1d4b481a996cbf7f8b1c72e939f655670f81`.
- Merge parents:
  - `ab4513ed6923f56a8e8ee6dd36cfbf0e8ff04465`;
  - PR #24 head `77645317b673b2e57dea803410126a61cdaf6d83`.
- Mandatory PR #25 code/package ancestor: `c713cee112e4b935b3a5b2c319d23fc6cbf180cb`.
- Exact tested implementation/workflow head: `32e17c228c9414a048484dc29dbf90d2cd264ff9`.
- Common base: `b712cadba6d035108c56dcc9746ff42443c3b07c`.
- Conflict-discovery Draft PR: `#26`, superseded by the canonical integration result.

Both mandatory source heads are ancestors of the tested canonical head. No squash, rebase or history rewrite was used.

## Semantic integration result

The ordinary merge exposed seven conflicts. They were resolved field-by-field rather than by unexplained whole-file `ours`/`theirs`:

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
- formula/source authority before conflicting legacy classifier;
- legacy classifier only as exact group+article fallback when formula/source authority is absent;
- direct KPI and exact revenue/quantity resolvers;
- three-sheet export;
- normal-user business UI without a technical Rules workflow.

## Exact-head CI and package

Canonical workflow:

`.github/workflows/canonical-preview-export.yml`

GitHub Actions run `31977644700` on exact head `32e17c228c9414a048484dc29dbf90d2cd264ff9`: `SUCCESS`.

Verification:

- compileall: PASS;
- unit: `119 passed`;
- integration: `78 passed, 6 skipped`;
- UI: `37 passed`;
- full regression: `234 passed, 6 skipped`;
- JavaScript syntax and diff hygiene: PASS;
- both mandatory ancestor checks: PASS;
- no tracked `.xls/.xlsx/.xlsm/.xlsb/.mxl`: PASS;
- combined wheel resources: PASS.

Windows package:

- offline x64 build: PASS;
- long-path launcher and short runtime fallback: PASS;
- health/home: PASS;
- synthetic upload, preview and three-sheet export: PASS;
- exact OPIU formula/source package smoke: PASS;
- restart persistence and PID replacement: PASS;
- `STOP_SERVICE` and port release: PASS;
- ZIP integrity: PASS;
- inner ZIP: `EXCEL_TO_OPIU_LIGHT_USER_32e17c228c94.zip`;
- inner ZIP SHA-256: `6593f1269098bdb01e294b29415ed8de66f569b85030254512075585be517931`;
- artifact: `EXCEL_TO_OPIU_LIGHT_CANONICAL_PREVIEW_EXPORT_WINDOWS`;
- artifact ID: `9271686445`;
- artifact digest: `sha256:2d7f841cbb23e17418867412cedfc894e93f7863e85cff983f1aa4cbbc4a6895`.

## Current action

`CREATE_FINAL_HANDOFF_AND_REPEAT_EXACT_DELIVERY_HEAD_CI`

After the final Git-visible handoff commit:

1. repeat the canonical workflow on the exact delivery head;
2. perform independent coordinator Git/diff/test/package QA;
3. return one exact package for Owner UX Smoke;
4. keep merge and release blocked pending explicit owner acceptance.

## Remaining evidence boundary

The previously accepted АЮ reconciliation remains the row-level real-owner evidence:

- source/output/exact numeric facts: `4 104 / 4 104 / 4 104`;
- missing, extra, value and context mismatches: `0`;
- formula-text numeric values: `0`.

The canonical GitHub workflow uses synthetic package data and does not commit or expose owner workbooks. Equivalent ПВ/ПС reconciliation remains an Owner Smoke evidence gate when those immutable files are available outside Git.

## Forbidden

- merge to `main` or release before independent QA and Owner UX Smoke;
- ADO, ODBC, direct SQL, 1C write or live write;
- fuzzy/contains/typo/case-only matching;
- universal Rules Engine or technical normal-user rules UI;
- real owner Excel/MXL, passwords, runtime DB or row-level financial output in Git;
- removal of either accepted parent capability without a new owner decision.
