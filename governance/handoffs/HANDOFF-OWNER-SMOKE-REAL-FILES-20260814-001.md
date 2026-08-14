# HANDOFF — Owner smoke on real AY/PV/PS workbooks

Date: 2026-08-14

## Git authority before fix

- Repository: `fitera2024-rgb/excel-transform-1c`
- Draft PR: `#22`
- Reviewed parent head: `41e8b9b6847a1cc55d58e7e027dec771117b0cde`
- Boundaries: `NO MERGE / NO RELEASE / NO ADO / NO ODBC / NO 1C / NO LIVE WRITE`

## Real owner evidence

Three owner-supplied workbooks were exercised locally outside Git. Originals were opened read-only/staged by exact bytes and remained SHA-256 unchanged. No workbook, decrypted copy, row-level financial data, amount, or export was committed.

| Workbook | Candidate | Source rows | Preview records | Exact ERP rows | CFO entries |
| --- | --- | ---: | ---: | ---: | ---: |
| AY budget 2026 | prepared budget | 195 | 2340 | 189 | 14 |
| PV budget 2026 | prepared budget | 184 | 2208 | 179 | 17 |
| PS budget 2026 | prepared budget | 179 | 2148 | 171 | 9 |
| PS workbook | Intalev OPIU fact 2025 | 165 | 1980 | 123 | 0 |

All four candidate exports opened as valid `OPIU Light` workbooks. The PV workbook retained 25 explicit reporting-unit conflicts instead of silently rewriting them.

## Defects found by real smoke

### 1. Source CFO was treated as if it were already an Intalev CFO

Real budget rows contain source CFO values such as organization-specific departments. Those values do not necessarily equal one of the 15 Intalev CFO catalog entries. The previous implementation therefore marked every budget row as blocked.

Fix:

- added persistent exact mapping `(reporting unit, source CFO) -> Intalev CFO source key`;
- preserved the existing exact mapping `Intalev CFO source key -> 1C node`;
- added explicit two-stage individual and bulk confirmation UI;
- no fuzzy, case-insensitive, typo, or display-name-only matching;
- one confirmation updates all 12 monthly records without rerun;
- mappings survive restart.

### 2. Real flat Intalev OPIU hierarchy was not parsed

The PS fact sheet encodes business hierarchy through adjacent columns and formatting, not only Excel indent/outline. It was detected but yielded zero source rows. A generic 12-month metrics sheet in the AY workbook could also be mistaken for OPIU.

Fix:

- added structural validation that rejects generic 12-month metric matrices;
- added flat Intalev OPIU parsing for expense sections, groups, leaves, and standalone business rows;
- technical totals and ratios remain excluded;
- reporting unit is retained from the source column;
- detection and reading use sequential scans where required for read-only workbook performance.

## Verification

Local focused checks:

- Python compile: PASS;
- JavaScript syntax: PASS;
- new synthetic regression tests: `6 passed`;
- real AY UI preview: PASS;
- real PS prepared-budget candidate selection and UI preview: PASS;
- real owner files unchanged by SHA-256: PASS;
- no real workbook or financial rows tracked: PASS.

New tests cover:

- real-style flat Intalev hierarchy;
- false-positive rejection for a generic 12-month matrix;
- persistent source-CFO two-stage mapping;
- exact-only behavior without case guessing;
- individual and bulk UI confirmation.

## Required next gate

Run the repository CI on the new exact head. Keep PR `#22` Draft. If CI is green, update PR `#22` to `OWNER_SMOKE_PASSED / READY_FOR_OWNER_ACCEPTANCE`; merge remains a separate explicit owner action.
