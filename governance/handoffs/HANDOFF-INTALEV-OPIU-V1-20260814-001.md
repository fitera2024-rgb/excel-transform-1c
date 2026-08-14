# Handoff — native Intalev OPIU preview and OPIU Light export

## Git authority

- Repository: `fitera2024-rgb/excel-transform-1c`
- Base: `feat/baselines-intalev-opiu-repair@5023ebb21bd6d9138ccc19ce3c2acf5e8b50db48`
- Work branch: `work/intalev-opiu-v1`

## Implemented

- structural recognition of an annual Intalev OPIU range without relying on the worksheet name;
- exact detection of twelve monthly period columns and source year;
- source CFO extraction from report metadata;
- hierarchy reconstruction from indentation and row outline levels;
- exclusion of technical totals while preserving leaf business articles;
- maximum-completeness preview with zero, negative and monthly-error values preserved;
- OPIU Light export with fixed headers, freeze panes, filter, widths and amount format;
- compatibility fallback for OOXML sharedStrings case differences;
- normal-mode read only for Intalev hierarchy extraction when row outline metadata is required; prepared-budget input remains streaming/read-only.

## Verification

- full regression: `79 passed, 1 skipped`;
- existing prepared-budget AЮ/PВ synthetic workflows preserved;
- no real Intalev file or business workbook committed.

## Boundaries

`DRAFT / NO MERGE / NO RELEASE / NO ADO / NO ODBC / NO 1C / NO LIVE WRITE / NO REAL BUSINESS EXCEL`

`READY_FOR_COORDINATOR_QA`
