# HANDOFF — V1 Excel transformation and preview implementation

HANDOFF-ID: `HANDOFF-CODEX-EXCEL-V1-20260812-001`  
DATE: `2026-08-12`  
REPOSITORY: `fitera2024-rgb/excel-transform-1c`  
ISSUE: `#2`  
TASK: `CODEX-TASK-EXCEL-V1-20260812-001`  
BRANCH: `feat/v1-excel-transform-preview`  
BASE: `836b3154c4c81ebc9c0ec3f8ef895afee5d47098`  
VERIFIED CODE HEAD: `47b7c7a04309122caf26760657ec5da2ea26d533`  
STATUS: `IMPLEMENTED / INDEPENDENT_QA_PASSED / OWNER_UX_SMOKE_REQUIRED / NO_MERGE`  
SAFETY: `NO ADO / NO LIVE WRITE / NO TEST OR PROD WRITE / NO DIRECT SQL WRITE TO ERP`

## Result

Реализован полный локальный V1 flow:

`references/context → Excel structural detection → validation → exact mapping/manual correction → 12-month normalization → maximum preview → error registry → OPIU Light export`.

Стек: Python 3.11+, FastAPI, server-rendered Jinja, SQLite, openpyxl, pytest.

## Implemented areas

- `core/` — DTO, structural detection, exact mapping, tax/amount rules, 12-month normalization and subtree union;
- `adapters/` — known ERP reference layouts, cached-value Excel reading, OPIU Light export and SQLite persistence;
- `application/` — context, immutable RUN-local snapshot, single-flight processing and field-specific corrections;
- `ui/` — context/reference forms, multiple-range choice, blocked reset, preview, exact source pointers, issue registry, corrections and export;
- `tests/` — synthetic structural facsimiles, unit, integration and UI smoke;
- `.github/workflows/ci.yml` — independent automated checks.

## Coordinator QA findings closed

1. **Real ERP references.** Direct structural adapters accept the documented article, organization and scenario exports. Users do not manually rebuild them into a flat template.
2. **Correction integrity.** A correction rebuilds the row state, keeps unrelated issues unresolved, invalidates/recomputes mapping after path changes, stores path + ERP selection under the new key, and shows saved/manual-vs-exact conflicts.
3. **Visible skipped month.** A nonnumeric/Excel-error month remains in preview and export as `Пропущено`, amount blank, with reason and exact sheet/cell pointer.
4. **Context conflict.** A non-empty Excel reporting unit different from the selected context creates `Требует внимания` and processing continues.

Additional hardening preserves exact article text, including trailing spaces, and does not perform fuzzy/case/typo correction.

## Test evidence

GitHub Actions `V1 CI` run `31598771451` for `47b7c7a04309122caf26760657ec5da2ea26d533`:

```text
python -m compileall -q src tests
PASS

python -m pytest tests/unit -q
14 passed

python -m pytest tests/integration -q
15 passed

python -m pytest tests/ui -q
7 passed, 1 third-party Starlette TestClient deprecation warning

python -m pytest -q
36 passed, 1 third-party Starlette TestClient deprecation warning

No tracked business Excel
PASS
```

## Synthetic fixtures

No business workbook/reference was committed. Tests create fictional `.xlsx` files at runtime, including structural facsimiles of:

- `СтатьиДоходовИРасходовЕРП.xlsx`;
- `ОрганизациииерархияЕРП.xlsx`;
- `СЦЕНАРИИ_СПР_ЕРП.xlsx`.

## Feature Baseline

All V1 IDs are `PRESERVED`; no `CHANGED_AUTHORIZED` or `BLOCKED_REGRESSION` was found.

Key evidence:

- INPUT/ERR/TRANS — structural detection, 12 months, localized errors and visible skipped rows;
- CONTEXT/SCENARIO/PERIOD — explicit context, persistent scenarios and year/month filtering;
- ORG/ACCESS — one nested tree and union of delegated subtrees;
- MAP — exact case-sensitive matching, manual fallback and visible conflicts;
- PREVIEW/UX/RESULT — maximum preview, corrections without rerun and 19-column business export;
- RUN/WRITE — immutable snapshot/single-flight and no ADO/write path.

## Known limitations

- Only the three documented ERP export families and the documented flat interchange schemas are supported; arbitrary undocumented layouts are not inferred.
- Cached formulas are read, not calculated.
- Catalogs/mappings persist; active preview objects are process-local and are not restored after restart.
- Access is a simple local subtree filter, not authentication or enterprise RBAC.
- One third-party TestClient deprecation warning does not affect behavior.

## Owner UX Smoke

1. Start the application and open `http://127.0.0.1:8000`.
2. Upload approved local copies of the three ERP reference exports.
3. Confirm codes/full paths, visible `Удалить` nodes and manual branch selection.
4. Select scenario/year/months and upload a budget Excel.
5. Confirm every source row produces 12 records; invalid month is visible as `Пропущено`.
6. Confirm issues contain file/sheet/cell/source-row pointers.
7. Apply ERP/tax/business correction and confirm the same RUN updates.
8. Confirm manual-vs-exact mapping conflict stays visible.
9. Export and inspect 19 business columns.
10. Upload a no-range workbook and confirm reset/reselect.

PR #4 remains Draft. Merge is not authorized until Owner UX Smoke is accepted.
