# Coordinator QA Contract — V1 implementation

TASK-ID: `COORDINATOR-QA-V1-20260812-001`  
LINKED IMPLEMENTATION: `Issue #2 / CODEX-TASK-EXCEL-V1-20260812-001`  
RISK: `M`  
STATUS: `WAITING_FOR_CODEX_DRAFT_PR`

## Goal

Независимо проверить результат Codex до любого merge/release и вернуть владельцу только реальные UX-решения или подтверждение готовности.

## Trigger

Начать проверку, когда в репозитории появится Draft implementation PR, связанный с Issue #2.

## Repository checks

1. Зафиксировать номер PR, exact base, exact head и branch.
2. Проверить, что реализация относится только к Issue #2 и Task Contract.
3. Проверить полный diff и список файлов, а не только описание PR.
4. Убедиться, что реальные бизнес-Excel, справочники, credentials, connection strings и secrets не попали в Git.
5. Убедиться, что нет ADO, TEST/PROD write или прямого SQL-write в 1С.
6. Проверить отсутствие fuzzy/typo/case autofix и скрытого расширения scope.
7. Проверить, что приложение остаётся локальным Light-конвертером, а не platform/multi-tenant системой.

## Functional verification

Проверить по коду, тестам и воспроизводимому запуску:

- structural detection независимо от имени листа;
- выбор при нескольких подходящих диапазонах;
- понятный blocked state при отсутствии диапазона;
- cached formula values без Excel recalculation;
- 12 месяцев на исходную строку, включая нули;
- локализацию ошибки одного месяца;
- сохранение остальных месяцев при ошибке общего поля;
- `continue with attention` и статусы `ОК / Требует внимания / Пропущено`;
- exact unique ERP mapping и ручной fallback;
- reusable mapping только по принятому key;
- сценарии, локальное persistence и ERP-unconfirmed marker;
- year/optional month selection;
- организационное дерево и объединение делегированных поддеревьев;
- отрицательные суммы со статусом внимания;
- пользовательские corrections без полного rerun;
- OPIU Light export без обязательных technical proof fields.

## Test verification

1. Получить фактические команды и полные результаты unit/integration/UI smoke tests.
2. Проверить, что synthetic fixtures действительно искусственные и достаточны для edge cases.
3. Сверить заявленные тесты с изменённым кодом.
4. Проверить CI/checks и расследовать любой fail/cancel/skip, влияющий на acceptance.
5. При необходимости запросить исправления через PR review; не merge-ить незавершённый PR.

## Feature Baseline

Для каждого затронутого ID из `governance/FEATURE_BASELINE.md` определить:

- `PRESERVED`;
- `CHANGED_AUTHORIZED`;
- `BLOCKED_REGRESSION`.

Любой `BLOCKED_REGRESSION` блокирует merge до исправления или нового owner decision.

## Required Codex handoff

Проверить наличие в Draft PR:

- exact base/head;
- stack и команды запуска;
- changed files;
- тесты и точные результаты;
- synthetic fixtures;
- Feature Baseline result;
- known limitations;
- `NO ADO / NO LIVE WRITE`;
- Owner UX Smoke instructions.

## Owner UX Smoke gate

До release владелец должен проверить бизнес-путь:

1. открыть приложение;
2. загрузить/выбрать справочники;
3. выбрать контекст;
4. выбрать synthetic или разрешённый локальный Excel;
5. увидеть preview и Реестр ошибок;
6. исправить реквизит/ERP mapping;
7. экспортировать результат.

Координатор возвращает владельцу краткую инструкцию и только те замечания, которые нельзя закрыть технической проверкой.

## Completion result

Финальный coordinator verdict:

- `READY_FOR_OWNER_UX_SMOKE`;
- `CHANGES_REQUESTED`;
- `BLOCKED_REGRESSION`;
- `READY_FOR_MERGE_AFTER_OWNER_SMOKE`.

Координатор не выполняет merge implementation PR без завершённых tests, handoff и Owner UX Smoke.