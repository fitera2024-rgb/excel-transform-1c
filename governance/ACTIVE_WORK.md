# Active Work

STATUS: `PRODUCT_ACCEPTED / USER_FLOW_ACCEPTED / SCENARIO_COUNT_FIX_VERIFIED / OWNER_UX_SMOKE_RETRY_REQUIRED / DRAFT_PR_4 / NO_LIVE_WRITE`

## Current phase

Первая vertical slice реализована в Draft PR `#4`:

`Excel → structural detection → validation → exact ERP mapping/manual correction → 12-month normalization → maximum preview → error registry → export`

Owner UX Smoke подтвердил:

- приложение запускается;
- новые подписи persistent-catalog UX отображаются;
- реальный справочник ERP-статей загружается полностью: `271`;
- реальный справочник организаций/узлов загружается полностью: `357`;
- справочник сценариев прочитан, но одна бизнес-строка была ошибочно отброшена: загружено `11` вместо `12`.

Строка `Сценарий отчетности КИК` содержала слово `Сценарий` и была ошибочно принята за повторный заголовок. Это дефект парсера, а не файла.

Дефект исправлен без изменения бизнес-scope.

## Current owner decisions

Владелец ранее явно уточнил:

- единый справочник организаций/узлов ERP загружается один раз;
- он сохраняется локально и используется для всех организаций и следующих запусков;
- пользователь выбирает организацию или узел из одного общего списка;
- повторная загрузка дополняет справочник и обновляет существующие записи по стабильному коду;
- полный список сценариев загружается один раз и сохраняется локально;
- последующие ERP-файлы и ручные добавления дополняют/обновляют список;
- стабильный локальный ID существующего сценария сохраняется.

Handoff:

- `governance/handoffs/HANDOFF-OWNER-UX-SMOKE-REFERENCE-CATALOGS-20260813-001.md`;
- `governance/handoffs/HANDOFF-OWNER-UX-SMOKE-SCENARIO-COUNT-20260813-002.md`.

## Git authority

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Branch: `feat/v1-excel-transform-preview`.
- Draft PR: `#4`, open, not merged.
- Accepted product base: `836b3154c4c81ebc9c0ec3f8ef895afee5d47098`.
- Reference-import fix code head: `7bc1e1bed0e9ea4d7641a5721e174ffe9f24c9ee`.
- Scenario-count fix code head: `dbe59a5d5e435d0cfa7f441ba833ca8507d70b6a`.
- ADO/live write: not implemented and not performed.

## Fix implemented

Header discovery and business-row classification are now separate:

- contains/fuzzy-like textual containment is allowed only to locate likely header cells;
- a data row is treated as a header only by exact normalized header equivalence;
- `Сценарий отчетности КИК` remains a normal scenario record;
- repeated ERP codes remain allowed for different scenario names;
- all twelve researched scenario rows are preserved.

## Test and CI evidence

GitHub Actions workflow: `V1 CI`, run `31641528467`.

Results for code head `dbe59a5d5e435d0cfa7f441ba833ca8507d70b6a`:

- compileall — PASS;
- unit — `14 passed`;
- integration — `19 passed`;
- UI smoke — `7 passed`;
- full regression — `40 passed`;
- no tracked business Excel — PASS.

A dedicated regression test builds a 12-row scenario export containing `Сценарий отчетности КИК` and verifies that all 12 records are returned.

## Current next action

`OWNER_UX_SMOKE_RETRY_SCENARIOS_THEN_CONTINUE`

Owner uses the latest PR head, restarts the service and reloads only the scenarios file.

Expected current reference counts:

- ERP articles: `271`;
- organizations/nodes: `357`;
- scenarios: `12`.

After the count is `12`, continue the existing Owner UX Smoke:

1. choose organization/node from the persistent common tree;
2. choose scenario and year;
3. upload the budget workbook;
4. inspect preview and issue registry;
5. apply one correction;
6. export OPIU Light.

## Forbidden

- merge before successful Owner UX Smoke;
- ADO connection or live write;
- TEST/PROD write;
- direct SQL write into 1C;
- real business Excel/reference files committed to Git;
- fuzzy/typo/case auto-match for ERP mapping;
- filename-based reference detection;
- per-organization duplicate reference catalogs;
- platform/multi-tenant/enterprise expansion.
