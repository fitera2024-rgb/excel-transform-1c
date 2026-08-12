# HANDOFF — Coordinator QA V1

HANDOFF-ID: `HANDOFF-COORDINATOR-QA-V1-20260812-001`  
DATE: `2026-08-12`  
REPOSITORY: `fitera2024-rgb/excel-transform-1c`  
IMPLEMENTATION ISSUE: `#2`  
QA ISSUE: `#3`  
PR: `#4`  
BRANCH: `feat/v1-excel-transform-preview`  
ACCEPTED PRODUCT BASE: `836b3154c4c81ebc9c0ec3f8ef895afee5d47098`  
PR BASE AT QA: `b57250a4dcc6a2b0442b200070411dc66a58ae0e`  
VERIFIED CODE HEAD: `47b7c7a04309122caf26760657ec5da2ea26d533`  
CI RUN: `31598771451`  
VERDICT: `READY_FOR_OWNER_UX_SMOKE`  
MERGE: `NOT PERFORMED`  
WRITE: `NO ADO / NO LIVE WRITE`

## Answer-first result

Независимая проверка реализации V1 завершена. Четыре блокирующих замечания первого review закрыты кодом и regression tests. Технических regressions, scope expansion или write-path не обнаружено.

Следующий gate — короткий Owner UX Smoke на локальном интерфейсе. До его принятия PR #4 остаётся Draft.

## Closed findings

### 1. Real reference imports

Прямо поддерживаются документированные структуры:

- `СтатьиДоходовИРасходовЕРП.xlsx`;
- `ОрганизациииерархияЕРП.xlsx`;
- `СЦЕНАРИИ_СПР_ЕРП.xlsx`.

Парсер использует структурные заголовки, indentation/outline и codes. Он не делает fuzzy/case/typo correction и сохраняет точный текст ERP-статьи, включая значимые trailing spaces.

### 2. Corrections and ERP remapping

- исправление одного поля не закрывает проблему другого поля;
- после изменения группы/статьи старый ERP-код не остаётся молча;
- path + ERP correction сохраняется по новому reusable key;
- saved manual mapping, конфликтующий с exact path, остаётся видимым пользователю;
- preview обновляется в том же RUN без полного rerun.

### 3. Visible skipped month

Excel error/non-numeric month создаёт отдельную месячную запись:

- status `Пропущено`;
- amount blank;
- reason visible;
- exact sheet/cell pointer visible in preview and error registry;
- other 11 months remain.

The skipped record is also preserved in OPIU Light export.

### 4. Reporting-unit conflict

Excel reporting unit that contradicts the selected context creates a localized attention issue with exact source pointer. Selected context remains authority and processing continues.

## Test evidence

GitHub Actions `V1 CI` run `31598771451` on `47b7c7a04309122caf26760657ec5da2ea26d533`:

| Check | Result |
|---|---:|
| Compile source/tests | PASS |
| Unit | 14 passed |
| Integration | 15 passed |
| UI smoke | 7 passed |
| Full regression | 36 passed |
| Tracked business Excel guard | PASS |

One third-party Starlette TestClient deprecation warning is non-blocking.

## Scope verification

Confirmed absent:

- ADO connection and write adapter;
- TEST/PROD/direct SQL write;
- real business workbooks committed to Git;
- fuzzy/typo/case auto-match;
- automatic source reconstruction from department calculation sheets;
- multi-tenant/platform/enterprise RBAC/queues/rules engine.

## Feature Baseline verdict

`PRESERVED`

No `CHANGED_AUTHORIZED`.
No `BLOCKED_REGRESSION`.

## Known limitations

- Arbitrary undocumented reference layouts are not inferred.
- Formula values must be cached by Excel; the service does not calculate formulas.
- Active preview state is process-local; catalogs, scenarios, mappings and overrides persist.
- Access is local subtree filtering, not user authentication.

## Owner UX Smoke

Run the local service and check:

1. The three ERP reference exports upload without manual reshaping.
2. Organization options show code/full path; `Удалить` entries remain visible.
3. Manual organization selection is required for `ПС`.
4. `ПЛАН 2026`, year and optional months can be selected.
5. A budget workbook produces 12 monthly records per source row, including zero.
6. Attention and skipped rows remain in the main preview with source pointers.
7. Manual ERP/tax/business correction updates the same RUN.
8. Manual-vs-exact ERP conflict remains visible instead of being silently replaced.
9. OPIU Light export contains 19 business columns and no proof/SHA/internal-path fields.
10. A workbook without a prepared range shows reset/reselect.

Owner result must be one of:

- `UX_SMOKE_ACCEPTED`;
- `UX_CHANGES_REQUESTED`.

Only `UX_SMOKE_ACCEPTED` permits coordinator to mark the PR ready for merge.
