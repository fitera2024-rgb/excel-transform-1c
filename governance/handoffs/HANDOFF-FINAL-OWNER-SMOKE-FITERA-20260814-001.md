# Handoff — final Owner Smoke package with FITERA UI

## Status

`IMPLEMENTED / REAL_FILES_PASSED / WINDOWS_PACKAGE_CI_PENDING / DRAFT / NO_MERGE / NO_LIVE_WRITE`

## Git authority

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Canonical integration base: `integration/baselines-intalev-opiu-v1@41e8b9b6847a1cc55d58e7e027dec771117b0cde`.
- Parent Draft PR: `#22`, open and not merged.
- Final branch/head and package artifact are recorded by the final CI run and PR comment after publication.

## Owner decisions implemented

1. A clean package contains baseline ERP articles, organization nodes, scenarios and Intalev CFOs.
2. `Загрузить / дополнить` preserves packaged baseline records and merges only by exact stable identity.
3. Reference and business workbooks use the same content-based preparation boundary.
4. Ordinary OOXML, encrypted OOXML, legacy BIFF/XLS, SpreadsheetML XML and narrowly repairable OOXML are supported without Excel COM.
5. The original input remains unchanged; decrypt/convert/repair uses a separate RUN-local working copy.
6. Annual Intalev OPIU is structurally recognized and exported as OPIU Light.
7. ERP, tax and CFO retain separate explicit checkboxes/actions; CFO mappings persist across restart.
8. The normal UI uses the owner-provided FITERA visual reference while preserving endpoints, input names and JavaScript/test hooks.
9. ADO, ODBC, 1C write and live write remain absent.

## Packaged baselines

A brand-new runtime starts with:

- ERP articles: `271`;
- organizations/nodes: `357`;
- scenarios: `12`;
- Intalev CFOs: `16`.

The 16-CFO baseline is normalized from the owner-supplied current classifier. No source Excel is tracked in Git or bundled as business evidence.

## Repair and intake changes

- reference imports now pass through the content-based workbook preparation adapter;
- a shared-strings part with incorrect OOXML filename case is canonicalized together with content-type and relationship references;
- true `.xls` and a BIFF file mislabeled `.xlsx` are accepted by signature;
- encrypted OOXML stays distinct from legacy BIFF and requires only transient request password handling;
- unsafe paths, duplicate/conflicting parts, unsupported ZIP structure and ambiguous XML damage fail closed;
- launcher/package checks include `olefile` and `xlrd`.

## Real owner-file evidence

Real files were supplied outside Git and processed in a fresh isolated runtime.

### Intalev CFO classifier

- structurally opened after OOXML compatibility repair;
- imported records: `16`;
- catalog after restart: `16`;
- original file hash unchanged.

### Annual Intalev OPIU

- selected sheet: `TDSheet`;
- detected header row: `4`;
- detected business range: rows `7–663`;
- source business rows: `475`;
- monthly records: `5700`;
- zero amounts preserved: `4191`;
- negative amounts preserved: `39`;
- OPIU Light export opened successfully with `5700` data rows and all 12 months;
- CFO mapping for the exact source CFO was bulk-confirmed and persisted after restart;
- tax-not-required was applied to `475` source rows without rerun;
- `rerun_count = 0`;
- original file hash unchanged.

### Protected AЮ budget

- original encrypted OOXML accepted through the normal upload path;
- selected prepared-budget range: rows `7–201`;
- source rows: `195`;
- monthly records/export rows: `2340`;
- original file hash unchanged.

### Protected ПВ budget

- original encrypted OOXML accepted through the normal upload path;
- selected prepared-budget range: rows `7–191`;
- source rows: `184`;
- monthly records/export rows: `2208`;
- original file hash unchanged.

The owner-supplied password was used transiently and is intentionally absent from this handoff, Git, logs, filenames and runtime metadata.

## HTTP/UI evidence

A real local Uvicorn server received full multipart uploads:

- full-size protected AЮ upload: accepted, explicit candidate selection, preview `2340`;
- full-size protected ПВ upload: accepted, preview `2208`;
- annual Intalev OPIU upload: accepted, preview `5700`;
- the historical empty `503` path did not reproduce;
- real CFO classifier import through `/references`: PASS;
- native CFO bulk checkbox/action through `/confirm-filled-cfo`: PASS;
- native tax bulk checkbox/action through `/confirm-tax-not-required`: PASS;
- status text rendered after confirmation: PASS;
- export after confirmations: PASS;
- CFO mapping after application restart: PASS.

## Automated verification before Windows packaging

With all real-file environment gates enabled:

- `python -m compileall -q src tests scripts`: PASS;
- full regression: `106 passed`;
- `node --check src/excel_transform_1c/ui/static/run.js`: PASS;
- `git diff --check`: PASS;
- tracked business Excel: `0`.

The final Windows CI must repeat source tests, build a Python 3.11 x64 offline wheelhouse including `olefile` and `xlrd`, run the actual package launcher twice, verify port cleanup, `/health`, home page, STOP_SERVICE and upload/export package smoke, then publish the exact ZIP artifact.

## Boundaries

`NO MERGE / NO RELEASE TO PRODUCTION / NO ADO / NO ODBC / NO 1C WRITE / NO LIVE WRITE / NO REAL BUSINESS EXCEL IN GIT`

## Final gate

After the Windows artifact succeeds and is downloaded/inspected, status may advance to:

`READY_FOR_OWNER_UX_SMOKE`
