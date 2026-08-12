# Active Work

STATUS: `PRODUCT_ACCEPTED / USER_FLOW_OWNER_REFINED / HIERARCHY_OPEN_ACCESS_ALL_YEAR_CI_PASSED / OWNER_UX_SMOKE_CONTINUE / DRAFT_PR_4 / NO_LIVE_WRITE`

## Current phase

Первая vertical slice реализована в Draft PR `#4`:

`Excel → structural detection → validation → exact ERP mapping/manual correction → 12-month normalization → maximum preview → error registry → export`

Owner UX Smoke уже подтвердил:

- приложение запускается;
- persistent ERP-справочники работают;
- ERP-статьи загружены: `271`;
- организации/узлы загружены: `357`;
- сценарий виден в форме;
- дефект `Сценарий отчетности КИК` исправлен и покрыт тестом.

## Current owner decisions

Во время UX Smoke владелец уточнил:

- единый справочник организаций/узлов загружается один раз и сохраняется локально;
- полный список сценариев загружается один раз и затем дополняется;
- отдельный блок `Область доступа` не нужен;
- всем пользователям локального сервиса доступно всё дерево организаций;
- делегирование/effective-access фильтрация удаляются из V1;
- организация выбирается иерархически: верхняя ветка → сам верхний или любой нижний узел;
- период содержит явную галочку `Весь год`, включённую по умолчанию;
- после снятия `Весь год` пользователь обязан выбрать хотя бы один месяц.

Exact handoff:

`governance/handoffs/HANDOFF-OWNER-UX-ORG-PERIOD-20260813-003.md`

## Implementation

- удалена карточка области доступа и endpoint делегирования из normal UI;
- при старте очищается legacy delegation state старых Draft-версий, поэтому узлы больше не скрываются;
- добавлен двухэтапный иерархический выбор организации;
- выбор верхней ветки автоматически выбирает её верхний узел и открывает всё поддерево;
- сценарий остаётся отдельным видимым селектором;
- добавлена галочка `Весь год` и управляемый выбор месяцев;
- добавлена server-side validation периода;
- User Flow и Feature Baseline синхронизированы с owner decision.

## Git authority

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Branch: `feat/v1-excel-transform-preview`.
- Draft PR: `#4`, open, not merged.
- Accepted product base: `836b3154c4c81ebc9c0ec3f8ef895afee5d47098`.
- Hierarchy/open-access/all-year code and regression head: `7e7d7ec26ecaa303f33eef7db93e6577358a7163`.
- Complete tested package before this Active Work update: `7f606a66aa4344ce1f42681245b52165da1da8b1`.
- ADO/live write: not implemented and not performed.

## Test and CI evidence

GitHub Actions `V1 CI`, run `31643909787`:

- compileall — PASS;
- unit — `14 passed`;
- integration — `19 passed`;
- UI smoke — `11 passed`;
- full regression — `44 passed`;
- no tracked `.xlsx/.xls/.xlsm` — PASS.

New regression coverage verifies:

- hierarchy selectors are rendered with root/subtree metadata;
- the access-rights card is absent;
- stale legacy delegation state is cleared and all nodes remain visible;
- the scenario selector remains visible;
- `Весь год` is checked by default;
- selected months filter the view without destroying the full 12-month result;
- an empty period after removing `Весь год` is rejected clearly.

## Feature Baseline result

- `ORG-002`: `CHANGED_AUTHORIZED`;
- `PERIOD-001`: `CHANGED_AUTHORIZED`;
- `ACCESS-001..004`: `REMOVED_AUTHORIZED`;
- `UX-004`, `UX-005`: accepted and implemented;
- all unrelated V1 baseline IDs: `PRESERVED`.

## Current next action

`OWNER_UX_SMOKE_HIERARCHY_PERIOD_THEN_BUDGET`

Owner updates/restarts the latest PR head while preserving `runtime/local.db`, then checks:

1. counters remain `271 / 357 / 12`;
2. the `Область доступа` card is absent;
3. selecting a top branch exposes only that complete subtree;
4. the top node itself or any child can be selected;
5. the scenario is visible;
6. `Весь год` is checked by default;
7. after unchecking it, months become available;
8. budget preview, one correction and export complete successfully.

## Forbidden

- merge before successful Owner UX Smoke;
- ADO connection or live write;
- TEST/PROD write;
- direct SQL write into 1C;
- real business Excel/reference files committed to Git;
- fuzzy/typo/case auto-match for ERP mapping;
- filename-based reference detection;
- reintroduction of local access-rights complexity without a new owner decision;
- platform/multi-tenant/enterprise expansion.
