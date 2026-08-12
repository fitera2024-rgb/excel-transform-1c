# Active Work

STATUS: `PRODUCT_ACCEPTED / USER_FLOW_ACCEPTED / IMPLEMENTATION_QA_PASSED / READY_FOR_OWNER_UX_SMOKE / DRAFT_PR_4 / NO_LIVE_WRITE`

## Current phase

Discovery, Product Contract, Architecture Light boundaries and User Flow V1 завершены и приняты владельцем.

Первая vertical slice реализована в Draft PR `#4`:

`Excel → structural detection → validation → exact ERP mapping/manual correction → 12-month normalization → maximum preview → error registry → export`

## Git authority

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Product PR: `#1`, merged.
- Accepted product base: `836b3154c4c81ebc9c0ec3f8ef895afee5d47098`.
- Implementation branch: `feat/v1-excel-transform-preview`.
- PR base at QA: `b57250a4dcc6a2b0442b200070411dc66a58ae0e`.
- Independently verified code head: `47b7c7a04309122caf26760657ec5da2ea26d533`.
- Implementation PR: `#4`, open, Draft, not merged.
- ADO/live write: not implemented and not performed.

## Independent coordinator QA

Coordinator QA Issue: `#3`.

Exact QA handoff:

`governance/handoffs/HANDOFF-COORDINATOR-QA-V1-20260812-001.md`

All four findings from the first review are closed in code and regression tests:

1. documented real ERP reference structures load directly;
2. user corrections are field-specific and ERP mapping is invalidated/recomputed safely;
3. invalid monthly value remains visible as `Пропущено` in preview and export;
4. reporting-unit conflict produces localized attention and does not block processing.

Additional hardening verified:

- trailing spaces/case are preserved for exact ERP matching; no hidden normalization;
- saved manual mapping conflicting with an exact ERP path remains visible;
- main preview displays the exact monthly source cell;
- simultaneous path + ERP correction persists the mapping under the new path.

## Test and CI evidence

GitHub Actions workflow: `V1 CI`, run `31598771451`.

Results for `47b7c7a04309122caf26760657ec5da2ea26d533`:

- `python -m compileall -q src tests` — PASS;
- unit — `14 passed`;
- integration — `15 passed`;
- UI smoke — `7 passed`;
- full regression — `36 passed`, one third-party Starlette TestClient deprecation warning;
- `No tracked business Excel` — PASS.

No CI failure, cancellation or skipped acceptance check remains.

## Feature Baseline

Coordinator result: `PRESERVED`.

No `CHANGED_AUTHORIZED` or `BLOCKED_REGRESSION` was found for V1. In particular:

- structural input detection and multiple-range choice preserved;
- 12 months including zero preserved;
- continue-with-attention and visible `Пропущено` preserved;
- exact/no-fuzzy ERP mapping and manual fallback preserved;
- scenarios, organizational tree, subtree delegation and local persistence preserved;
- corrections without full rerun preserved;
- OPIU Light export preserved;
- ADO/write boundaries preserved.

## Current next action

`OWNER_UX_SMOKE_PR_4`

Owner verifies the business path locally:

1. upload the three approved ERP reference exports;
2. select reporting unit, organization branch, scenario, year/months;
3. upload a budget Excel;
4. inspect preview and issue registry;
5. apply a manual correction;
6. export OPIU Light;
7. confirm blocked no-range/reset behavior.

After owner acceptance:

`READY_FOR_MERGE_AFTER_OWNER_SMOKE`

PR #4 remains Draft and must not be merged before the owner smoke result.

## Forbidden

- ADO connection or live write;
- TEST/PROD write;
- direct SQL write into 1C;
- real business Excel/reference files committed to Git;
- fuzzy/typo/case auto-match;
- hidden trimming or automatic correction of ERP article names;
- platform/multi-tenant/enterprise expansion;
- self-merge by an implementation agent.
