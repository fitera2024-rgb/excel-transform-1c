# HANDOFF — Owner UX Smoke: scenario count regression

HANDOFF-ID: `HANDOFF-OWNER-UX-SMOKE-SCENARIO-COUNT-20260813-002`  
DATE: `2026-08-13`  
REPOSITORY: `fitera2024-rgb/excel-transform-1c`  
PR: `#4`  
BRANCH: `feat/v1-excel-transform-preview`  
FIX CODE HEAD: `dbe59a5d5e435d0cfa7f441ba833ca8507d70b6a`  
STATUS: `FIXED / CI_PASSED / OWNER_UX_SMOKE_RETRY_REQUIRED / NO_MERGE`  
SAFETY: `NO ADO / NO LIVE WRITE`

## Owner observation

During the repeated Owner UX Smoke:

- ERP articles imported successfully: `271`;
- organizations/nodes imported successfully: `357`;
- scenarios imported without a screen error, but the stored count was `11` instead of the researched `12`.

Inspection of the real workbook confirmed twelve data rows. The missing business record was:

`Сценарий отчетности КИК`

## Root cause

The same permissive text-containment rule was used both:

1. to discover candidate header cells; and
2. to decide whether a parsed data value was itself a repeated header.

Because `Сценарий отчетности КИК` contains the word `Сценарий`, it was incorrectly discarded as a header-like row.

This was a parser defect. The workbook was valid.

## Fix

The responsibilities are separated:

- permissive containment remains available only during structural header discovery;
- once the data range is selected, a row is skipped as a header only when its normalized value exactly matches an approved header alias;
- scenario names containing words such as `Сценарий` are preserved as business data;
- repeated ERP codes across distinct scenario names remain supported.

## Regression test

Added:

`tests/integration/test_scenario_header_regression.py`

The fixture contains twelve scenario rows, repeated ERP codes and the exact value `Сценарий отчетности КИК`.

Assertions:

- parser returns exactly `12` rows;
- `Сценарий отчетности КИК` is present.

## Independent CI evidence

GitHub Actions `V1 CI`, run `31641528467`:

- compileall: PASS;
- unit: `14 passed`;
- integration: `19 passed`;
- UI smoke: `7 passed`;
- full suite: `40 passed`;
- no tracked `.xlsx/.xls/.xlsm`: PASS.

No real business workbook was committed.

## Owner UX Smoke retry

Use the latest PR head and restart the local service.

The already loaded global ERP article and organization catalogs remain valid. Reload:

`СЦЕНАРИИ_СПР_ЕРП.xlsx`

Expected result:

`Сценарии: 12`

Then continue with organization/node selection, scenario/year selection, budget preview, one correction and OPIU Light export.

PR remains Draft. Merge is not authorized before owner acceptance.
