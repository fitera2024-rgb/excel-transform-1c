# HANDOFF — V1 Excel transformation and preview implementation

HANDOFF-ID: `HANDOFF-CODEX-EXCEL-V1-20260812-001`
DATE: `2026-08-12`
REPOSITORY: `fitera2024-rgb/excel-transform-1c`
ISSUE: `#2`
TASK: `CODEX-TASK-EXCEL-V1-20260812-001`
BRANCH: `feat/v1-excel-transform-preview`
BASE: `836b3154c4c81ebc9c0ec3f8ef895afee5d47098`
HEAD: exact implementation commit containing this handoff; pin the resulting SHA in the Draft PR
STATUS: `IMPLEMENTED / TESTED / DRAFT_REVIEW_REQUIRED / NO_MERGE`
SAFETY: `NO ADO / NO LIVE WRITE / NO TEST OR PROD WRITE / NO DIRECT SQL WRITE TO ERP`

## Result

Реализован полный локальный V1 flow:

`references/context → Excel structural detection → validation → exact mapping/manual correction → 12-month normalization → maximum preview → error registry → OPIU Light export`.

Стек: Python 3.11+, FastAPI, server-rendered Jinja, SQLite, openpyxl, pytest.
Приложение остаётся одним локальным сервисом без SPA, multi-tenant слоя,
enterprise RBAC, очередей, plugin/rules framework или write adapter.

## Changed areas

- `src/excel_transform_1c/core/` — schema detection, domain DTO, tax/amount rules,
  exact case-sensitive full-path ERP mapping, reusable mapping key, 12-month
  normalization and organization subtree union;
- `src/excel_transform_1c/adapters/` — cached-value Excel read, OPIU Light
  export, synthetic/local reference import and local SQLite persistence;
- `src/excel_transform_1c/application/` — context validation, immutable
  RUN-local snapshot, single-flight processing, corrections without rerun;
- `src/excel_transform_1c/ui/` — reference/scenario/context forms, multiple-range
  choice, blocked reset, preview, issue registry, corrections and export;
- `tests/` — generated synthetic workbooks plus unit, integration and UI smoke;
- README/Architecture/Active Work/Task Contract — run commands, exact base and
  implementation status.

## Coordinator QA changes addressed

- direct structural adapters now accept the documented hierarchical ERP article,
  organization and scenario exports; no manual conversion to a flat template is
  required;
- corrections resolve only the field actually changed, invalidate/recompute an
  ERP code after a path change, save simultaneous path + ERP selection under the
  new key, and surface saved-manual-versus-exact conflicts;
- an unreadable monthly value now remains in the main preview/export as
  `Пропущено` with a blank amount and exact source pointer;
- a non-empty Excel reporting unit that contradicts the selected unit creates a
  localized attention issue while processing continues.

## Run commands

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m excel_transform_1c.main
```

Open `http://127.0.0.1:8000`.

## Test evidence

```text
.\.venv\Scripts\python.exe -m pytest tests/unit -q
12 passed

.\.venv\Scripts\python.exe -m pytest tests/integration -q
14 passed

.\.venv\Scripts\python.exe -m pytest tests/ui -q
6 passed, 1 third-party Starlette TestClient deprecation warning

.\.venv\Scripts\python.exe -m pytest -q
32 passed, 1 third-party Starlette TestClient deprecation warning

.\.venv\Scripts\python.exe -m compileall -q src tests
PASS
```

Served-browser smoke against `http://127.0.0.1:8000`:

- synthetic reference upload: ERP 3, organizations 5, scenarios 1;
- new `ПЛАН 2027` persisted and marked ERP-unconfirmed;
- attention workbook: 2 source rows → 24 records, issue registry 1;
- manual ERP correction: same RUN, rerun count 0, issue registry 1 → 0;
- OPIU Light download completed;
- no-range workbook showed blocked state and reset returned to start;
- browser console errors: 0.

## Synthetic fixtures

No workbook or reference from the business evidence was opened, copied or
committed. Tests generate fictional `.xlsx` bytes at runtime under pytest temp
directories, including structural facsimiles of all three documented ERP export
layouts. Served-browser smoke used the same generator under an ignored temporary
runtime directory, removed after verification. `.gitignore` continues to reject
all `.xlsx/.xls/.xlsm` files.

## Feature Baseline

| IDs | Result | Evidence |
|---|---|---|
| SCOPE-001, ENG-001..002 | PRESERVED | single local service; no platform/RBAC/queues/plugins |
| INPUT-001..005 | PRESERVED | upload, structural detection, prepared range only, cached values, explicit candidate choice |
| VAL-001, ERR-001..006 | PRESERVED | business-language issue registry, local error handling, exact pointer, blocked only for unusable source |
| TAX-001..002, AMOUNT-001 | PRESERVED | tax normalization/attention and negative preservation tests |
| CONTEXT-001..004, REPORT-001 | PRESERVED | manual reference-backed context and fixed report type |
| SCENARIO-001..004 | PRESERVED | alias, stable ID, restart persistence, ERP-unconfirmed marker |
| PERIOD-001..002 | PRESERVED | year/month UI filter; internal result remains all 12 months |
| ORG-001..004, REF-001 | PRESERVED | one tree, manual node selection, full path/code, `Удалить` remains visible |
| ACCESS-001..004 | PRESERVED | union of delegated subtrees, deduplication, no parent/sibling expansion |
| MAP-001..005 | PRESERVED | exact case-sensitive unique path, manual fallback, accepted reusable key, conflict handling |
| TRANS-001..003 | PRESERVED | core independent of UI/write; 12 months with zero; monthly error localization |
| PREVIEW-001..003, UX-001..003 | PRESERVED | maximum preview, no quarantine, explicit correction without rerun, business UI |
| TRACE-001 | PRESERVED | original and selected override values stored locally |
| RESULT-001..002 | PRESERVED | 19-field business OPIU Light export, no proof fields |
| RUN-001..003 | PRESERVED | RUN-ID, immutable snapshot, same input/context/candidate single-flight |
| ADO-001, WRITE-001..003 | PRESERVED | no ADO or ERP write path exists; preview remains independent of future write |
| REL-001, GOV-001..003 | PRESERVED | exact accepted base, Draft-only delivery, no merge |

No `CHANGED_AUTHORIZED` or `BLOCKED_REGRESSION` result was found.

## Known limitations

- V1 reference imports support the three documented current ERP export structures
  and a flat synthetic-safe interchange schema; undocumented layouts are not inferred.
- openpyxl reads cached formula results but does not calculate formulas. A workbook
  saved without cached values may produce localized monthly attention/skips.
- scenarios, references, delegations, manual mappings and overrides persist in
  SQLite; active preview objects remain process-local and are not restored after
  a service restart.
- access is a simple local delegation filter, not authentication or enterprise RBAC.
- UI tests use FastAPI TestClient; an additional real served-browser flow was
  executed separately. The TestClient suite emits one dependency deprecation warning.

## Owner UX Smoke

1. Start the service with the commands above and open `http://127.0.0.1:8000`.
2. Upload approved sanitized copies in the documented reference interchange schemas.
3. Confirm organization choices include code/full path and that `Удалить` nodes
   are visible; select the required branch manually for `ПС`.
4. Select `ПЛАН 2026`, year 2026 and no month filter; upload a sanitized workbook.
5. If several candidates appear, select one explicitly. Confirm two source rows
   produce 24 monthly records including zeros.
6. Confirm attention records remain in the main preview and exact file/sheet/cell
   pointers appear in the issue registry.
7. Apply a manual ERP correction and confirm the same preview updates without rerun.
8. Add a scenario and confirm the ERP-unconfirmed marker remains after restart.
9. Export OPIU Light and inspect the 19 business columns; confirm no SHA, proof JSON,
   internal path or technical blocker fields.
10. Upload a no-range sanitized workbook and confirm blocked reselect/reset.

Owner/Coordinator decides review, UX acceptance and merge. Codex does not merge.
