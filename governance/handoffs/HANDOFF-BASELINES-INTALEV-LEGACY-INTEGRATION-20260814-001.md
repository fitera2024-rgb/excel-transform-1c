# Handoff — integrated baselines, Intalev OPIU and legacy Excel intake

## Git authority

- Repository: `fitera2024-rgb/excel-transform-1c`
- Base: `feat/baselines-intalev-opiu-repair@5023ebb21bd6d9138ccc19ce3c2acf5e8b50db48`
- Integration branch: `integration/baselines-intalev-opiu-v1`
- Components:
  - `work/baseline-catalogs-v1`;
  - `work/intalev-opiu-v1`;
  - `work/legacy-excel-intake-v1`.

## Integrated behavior

1. A new installation starts with exact packaged ERP, organization, scenario and Intalev-CFO baselines.
2. User imports replace the corresponding initial baseline once, then merge by exact stable identity.
3. Workbook type is detected from bytes/internal parts rather than the filename suffix.
4. OOXML, encrypted OOXML, BIFF and SpreadsheetML XML remain distinct formats.
5. Original input is preserved; conversion or repair uses a separate working OOXML file.
6. Recoverable OOXML is repaired conservatively with path, member-count and decompressed-size checks.
7. Native annual Intalev OPIU reports are detected structurally, converted to maximum-completeness preview and exported as OPIU Light.
8. Existing prepared-budget, protected-upload, ERP mapping, attention, bulk-confirmation and export behavior remains covered.

## Verification

- compile: PASS;
- full integrated regression: `94 passed, 5 skipped`;
- skipped tests require separately supplied real owner workbooks/environment variables;
- wheel build: PASS;
- packaged baseline resources and workbook-repair module present: PASS;
- tracked business Excel: `0`;
- no password, token, runtime DB, local absolute path or real financial workbook added.

## Boundaries

`DRAFT / NO MERGE / NO RELEASE / NO ADO / NO ODBC / NO 1C / NO LIVE WRITE / NO REAL BUSINESS EXCEL`

`READY_FOR_COORDINATOR_QA`
