# Active Work

STATUS: `PRODUCT_ACCEPTED / USER_FLOW_ACCEPTED / REFERENCE_IMPORT_FIX_VERIFIED / OWNER_UX_SMOKE_RETRY_REQUIRED / DRAFT_PR_4 / NO_LIVE_WRITE`

## Current phase

Первая vertical slice реализована в Draft PR `#4`:

`Excel → structural detection → validation → exact ERP mapping/manual correction → 12-month normalization → maximum preview → error registry → export`

Во время Owner UX Smoke приложение успешно запустилось, но реальные ERP-справочники были отклонены сообщением `Не найден заголовок известной ERP-выгрузки`.

Проблема исправлена без изменения бизнес-scope.

## Current owner decisions

Владелец явно уточнил:

- единый справочник организаций/узлов ERP загружается один раз;
- он сохраняется локально и используется для всех организаций и следующих запусков;
- пользователь выбирает организацию или узел из одного общего списка;
- повторная загрузка дополняет справочник и обновляет существующие записи по стабильному коду, не создавая копию на каждую организацию;
- полный список сценариев загружается один раз;
- сценарии сохраняются локально;
- последующие ERP-файлы и ручные добавления дополняют/обновляют список, не удаляя ранее загруженные сценарии;
- стабильный локальный ID существующего сценария сохраняется.

Exact handoff:

`governance/handoffs/HANDOFF-OWNER-UX-SMOKE-REFERENCE-CATALOGS-20260813-001.md`

## Git authority

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Branch: `feat/v1-excel-transform-preview`.
- Draft PR: `#4`, open, not merged.
- Accepted product base: `836b3154c4c81ebc9c0ec3f8ef895afee5d47098`.
- Previous reviewed head: `75d6d3e91da40550840879500bf8eebe07527b80`.
- Reference-import fix code head: `7bc1e1bed0e9ea4d7641a5721e174ffe9f24c9ee`.
- ADO/live write: not implemented and not performed.

## Fix implemented

- known ERP headers may be located on different header rows;
- article/organization/scenario header aliases are recognized structurally;
- the most plausible name/code column pair is selected by data evidence, not filename;
- numeric ERP codes with zero number formats retain leading zeroes;
- organization and ERP-article catalogs are merged globally by code;
- repeated imports update matching codes and append new codes;
- scenarios are upserted by canonical name + year with stable local ID;
- UI explains one-time persistent loading and incremental supplements.

## Test and CI evidence

GitHub Actions workflow: `V1 CI`, run `31636475885`.

Results for code head `7bc1e1bed0e9ea4d7641a5721e174ffe9f24c9ee`:

- compileall — PASS;
- unit — `14 passed`;
- integration — `18 passed`;
- UI smoke — `7 passed`;
- full regression — `39 passed`;
- no tracked business Excel — PASS.

The new tests cover:

- split/multi-row ERP headers;
- preservation of zero-padded codes;
- one global persistent organization catalog;
- incremental organization updates/additions;
- one persistent scenario catalog;
- incremental scenario additions with stable IDs.

## Current next action

`OWNER_UX_SMOKE_RETRY_REFERENCE_UPLOAD`

Owner downloads/replaces the application code from the latest PR head, restarts the local service, and retries:

1. ERP articles;
2. organizations;
3. scenarios.

Expected reference counts for the researched files:

- ERP articles: `271`;
- organizations/nodes: `357`;
- scenarios: `12`.

If those imports pass, continue the existing Owner UX Smoke with organization/node selection, budget preview, correction and export.

## Forbidden

- merge before successful Owner UX Smoke;
- ADO connection or live write;
- TEST/PROD write;
- direct SQL write into 1C;
- real business Excel/reference files committed to Git;
- fuzzy/typo/case auto-match;
- filename-based reference detection;
- per-organization duplicate reference catalogs;
- platform/multi-tenant/enterprise expansion.
