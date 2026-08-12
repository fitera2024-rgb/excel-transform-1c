# Codex Task Contract — V1 Excel transformation and preview

TASK-ID: `CODEX-TASK-EXCEL-V1-20260812-001`  
WORK-ID: `WORK-EXCEL-V1-20260812-001`  
CR-ID: `CR-EXCEL-V1-20260812-001`  
RISK: `M`  
STATUS: `PREPARED / BLOCKED_BY_PRODUCT_PR_MERGE / DO_NOT_START_YET`  
PREPARED AGAINST PRODUCT HEAD: `fd8f40e812c8378b3a2b1d5dbdbd409f831f6704`  
BASE COMMIT FOR IMPLEMENTATION: `PIN_EXACT_MERGED_PRODUCT_HEAD_AFTER_PR_1_MERGE`  
TARGET BRANCH: `feat/v1-excel-transform-preview`

## Goal

Реализовать первую работающую vertical slice локального конвертера:

`Excel → structural detection → validation → ERP mapping → user corrections → 12-month normalization → preview → export`

Без ADO и без записи в 1С/БД.

## Required reading

1. `docs/PRODUCT.md`
2. `docs/USER_FLOW.md`
3. `docs/ARCHITECTURE.md`
4. `governance/DECISIONS.md`
5. `governance/FEATURE_BASELINE.md`
6. `governance/handoffs/HANDOFF-EXCEL-LOGIC-20260812-001.md`
7. `governance/handoffs/HANDOFF-OWNER-DECISIONS-20260812-002.md`
8. `AGENTS.md`

## Technical direction

Использовать самое простое поддерживаемое локальное решение.

Предпочтительный baseline:

- Python application;
- FastAPI или эквивалентный лёгкий local web layer;
- server-rendered UI/HTMX либо столь же простой подход без обязательного тяжёлого SPA;
- SQLite либо эквивалентное локальное постоянное хранилище;
- `openpyxl` или эквивалент для чтения структуры и cached formula values;
- `pytest` для core/integration tests;
- Playwright либо эквивалент только для минимального UI smoke/happy/attention flow.

Codex может выбрать эквивалентный более простой stack, но должен сначала обновить `docs/ARCHITECTURE.md` с обоснованием. Нельзя превращать задачу в platform architecture.

## Exact scope

### 1. Bootstrap application

Создать минимальную запускаемую локальную application structure по слоям:

- UI;
- Application / Workflow;
- Business Core;
- Adapters: Excel, References, Local persistence;
- Runs / Logs.

### 2. Reference loading

Поддержать локальную загрузку/обновление:

- ERP-справочника статей;
- дерева организаций/ЦФО/подразделений;
- справочника сценариев, если предоставлен.

Не hardcode-ить реальные бизнес-файлы и не коммитить их в Git.

### 3. Scenario catalog

Реализовать:

- канонизацию `ПЛАН_2026` → `ПЛАН 2026`, год `2026`;
- ERP-код `00010` как необязательный атрибут;
- стабильный local scenario ID;
- добавление сценария: наименование, год, необязательный комментарий;
- постоянное локальное хранение;
- видимость всем пользователям локального сервиса;
- отметку `Не подтверждён справочником ERP`;
- отсутствие write-ready для неподтверждённого сценария.

### 4. Context selection

Реализовать:

- фиксированный вид отчёта `Отчет о прибылях и убытках` / `ОтчетОПрибыляхИУбытках`;
- отдельные поля единицы отчёта и организационного узла;
- ручной выбор организационного узла при каждом запуске;
- дерево без автоматического скрытия по `Статус`, `Тип узла`, `Удалить`;
- отображение кода и полного пути;
- делегацию на любой узел и фильтрацию по объединению поддеревьев;
- выбор года и optional month filter;
- year-only → все 12 месяцев;
- month-only допустим при однозначном годе сценария.

### 5. Excel source detection and reading

- пользователь выбирает бюджетный Excel;
- подготовленный диапазон определяется структурно, не по имени листа;
- обязательны business columns и 12 месячных колонок;
- при нескольких кандидатах UI предлагает выбор;
- при отсутствии кандидата показывается понятное blocked state с reselect/reset;
- формулы читаются по cached calculated values;
- сервис не пересчитывает Excel;
- source pointer сохраняет file/sheet/row/cell/field/month.

### 6. Transformation and validation

- каждая исходная строка формирует все 12 месяцев, включая нули;
- Excel error конкретного месяца пропускает только эту месячную запись;
- ошибка общего поля не удаляет остальные месяцы;
- `0.2` → `20%`, `0.22` → `22%`;
- `?`, пустое и неоднозначный числовой `0` по налогообложению → `Требует внимания`;
- отрицательная сумма сохраняется и получает `Требует внимания` / `Отрицательная сумма`;
- ошибки вне официального диапазона не анализируются V1.

### 7. ERP mapping

- автоматически назначать ERP-код только при exact unique match по полной принятой иерархии/атрибутам;
- не использовать fuzzy, typo correction, case-insensitive autofix или самостоятельное игнорирование hierarchy;
- при unresolved mapping оставить запись в preview и предложить ручной выбор;
- reusable key ручного mapping: report type + `тип расходов → группа расходов → исходная статья`;
- при конфликте сохранённый mapping не применять молча.

### 8. Preview and error registry

Основной preview содержит максимально полный результат и статусы:

- `ОК`;
- `Требует внимания`;
- `Пропущено`.

Реестр проблем содержит максимум доступного контекста и точный source pointer.

Не создавать скрытый карантин.

### 9. User corrections

Разрешить явные исправления из загруженных справочников:

- ERP-код;
- налогообложение;
- департамент;
- ЦФО;
- группа;
- статья;
- другие доказанно справочные поля.

После исправления preview и error registry обновляются без полного перезапуска и без потери корректного результата.

### 10. Export

Экспортировать OPIU Light result с полями Product Contract. Не включать обязательные SHA, internal paths, proof JSON или technical blocker codes.

## MUST PRESERVE

Все IDs из `governance/FEATURE_BASELINE.md`, особенно:

- `INPUT-002..005`;
- `ERR-001..006`;
- `SCENARIO-001..004`;
- `PERIOD-001..002`;
- `ORG-001..004`;
- `ACCESS-001..004`;
- `MAP-001..005`;
- `TRANS-001..003`;
- `PREVIEW-001..003`;
- `AMOUNT-001`;
- `WRITE-001..003`.

## Allowed

- создать минимальный application scaffold;
- выбрать эквивалентный простой stack с документированным обоснованием;
- добавить искусственные/sanitized Excel fixtures;
- изменить `.gitignore`, чтобы разрешить только явно обозначенные synthetic fixtures, сохранив запрет на реальные business Excel;
- добавить unit/integration/e2e tests;
- добавить локальное migration/schema initialization для persistence.

## Forbidden

- ADO connection;
- TEST/PROD write;
- прямой SQL-write в 1С;
- использование или commit реальных Excel/справочников;
- fuzzy/typo/case auto-match;
- reconstruct source from department calculation sheets;
- multi-tenant architecture, enterprise RBAC, queues/event bus, plugin/rules framework;
- source-proof UI, mandatory hashes/digests;
- самостоятельный merge PR;
- расширение scope на прочие доходы или другие виды отчётов без нового owner decision.

## Acceptance Criteria

1. Приложение запускается локально по документированной команде.
2. Пользователь может загрузить synthetic reference files и выбрать/добавить сценарий.
3. Локальный сценарий сохраняется после restart.
4. Пользователь может выбрать год и optional months.
5. Пользователь может выбрать любой разрешённый organizational node; выбор не угадывается для `ПС`.
6. Synthetic Excel с подготовленным диапазоном распознаётся независимо от имени листа.
7. Две исходные строки дают ровно 24 monthly records, включая нули.
8. Formula cached values читаются без требования Paste Values.
9. Ошибка одной monthly cell не удаляет другие 11 месяцев.
10. Ошибка общего поля оставляет monthly records в preview как `Требует внимания`.
11. Exact unique ERP path получает код автоматически.
12. Неоднозначный/missing mapping требует ручного выбора и не блокирует весь preview.
13. Ручной mapping повторно применяется только по принятому key.
14. Отрицательная сумма сохраняется со статусом внимания.
15. Записи/узлы с `Удалить` не скрываются автоматически.
16. User correction обновляет preview и registry без полного rerun.
17. Экспорт содержит business fields и не содержит обязательных technical proof fields.
18. В коде отсутствует ADO/live write path.

## Required Tests

### Unit

- structural schema detection;
- 12-month normalization including zero;
- monthly error localization;
- shared-field attention behavior;
- tax normalization;
- negative amount behavior;
- exact ERP mapping and conflict handling;
- reusable mapping key;
- scenario alias and local identity;
- organization subtree union.

### Integration

- synthetic workbook with arbitrary sheet name;
- workbook with two candidate ranges;
- broken/no-range workbook;
- cached formula result path;
- local persistence across restart;
- export schema and row counts.

### UI smoke

- happy path to preview/export;
- attention path with manual ERP correction;
- add scenario and observe ERP-unconfirmed marker;
- blocked no-range state with reselect/reset.

## Required Handoff

В Draft PR указать:

- exact base/head;
- stack and run commands;
- changed files;
- tests and exact results;
- synthetic fixtures description;
- Feature Baseline table with `PRESERVED/CHANGED_AUTHORIZED/BLOCKED_REGRESSION`;
- known limitations;
- explicit confirmation `NO ADO / NO LIVE WRITE`;
- Owner UX Smoke instructions.

Codex must:

- start only after PR #1 is merged and exact merged product head is pinned;
- work only in a separate task branch;
- keep implementation PR Draft;
- not merge;
- not expand product scope;
- not perform live write.
