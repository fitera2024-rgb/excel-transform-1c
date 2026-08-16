# HANDOFF TASK-06-08: KPI-контекст и вычисленные месячные значения БДР

HANDOFF-ID: `HANDOFF-TASK-06-08-BDR-KPI-CONTEXT-VALUE-RESOLVER-20260816-001`

TASK-ID: `TASK-06-08-BDR-KPI-CONTEXT-VALUE-RESOLVER-20260816-001`

DATE: `2026-08-16`

BRANCH: `codex/task-06-08-bdr-kpi-context-value`

BASE SHA: `83c1f573c61cc0f0b086026bece02be8b0d66326`

FINAL SHA: `bb91ba628412399d4b84b5879be4b7d77513e195`

STATUS: `READY FOR OWNER UX SMOKE / NO MERGE / NO LIVE WRITE`

`FINAL SHA` — проверенный implementation commit. Этот handoff добавляется отдельным documentation-only commit и не меняет проверенную реализацию.

## Что изменено

- Добавлен business-safe DTO `KPIResult`: организация и код, исходный отдел, наименование родительского департамента, ЦФО и код, тип/название KPI, период и числовое значение.
- Полный БДР распознаёт единственную exact-колонку `Отдел` рядом с доказанной месячной схемой. Для KPI значение отдела берётся из той же исходной строки; доходные и расходные resolver-потоки не изменены.
- Для formula cell KPI адаптер читает только сохранённый вычисленный OOXML result `<v>` по exact координате `строка KPI × колонка месяца`. Формула, текст формулы и ссылка на ячейку не становятся значением результата.
- Cached-value fallback применяется только к KPI полного БДР; Excel calculation engine не добавлен, формула без сохранённого результата не вычисляется самостоятельно.
- Агрегация листа `Показатели` сохраняет границы департамента/ЦФО и не объединяет одинаковый KPI разных организационных контекстов.
- Во всех трёх листах `OPIU Light`, `ОПИУ`, `Показатели` KPI содержит организацию, код организации, департамент, отдел, ЦФО, код ЦФО, тип, показатель, период и числовое значение.
- Перед экспортом показываются счётчики `KPI найдено`, `KPI с организацией`, `KPI с периодом`, `KPI со значением`, `KPI экспортировано`.

## Изменённые файлы

- `scripts/owner_smoke_http.py`
- `src/excel_transform_1c/adapters/excel.py`
- `src/excel_transform_1c/application/service.py`
- `src/excel_transform_1c/core/detection.py`
- `src/excel_transform_1c/core/indicator_matching.py`
- `src/excel_transform_1c/core/kpi.py`
- `src/excel_transform_1c/core/models.py`
- `src/excel_transform_1c/ui/templates/run.html`
- `tests/helpers/workbooks.py`
- `tests/integration/test_article_indicator_workflow.py`
- `tests/integration/test_bdr_full_load_workflow.py`
- `tests/integration/test_packaged_opiu_classifier_workflow.py`
- `tests/integration/test_revenue_quantity_workflow.py`
- `tests/unit/test_bdr_full_load.py`
- `tests/unit/test_bdr_kpi_context_value.py`

## KPI обработано

Структурный regression/smoke БДР:

- KPI найдено: `6`;
- KPI с организацией: `6`;
- KPI с периодом: `6`;
- KPI со значением: `6`;
- KPI экспортировано: `6`;
- месячных KPI-записей: `72`;
- всего показателей БДР: `14`;
- всего экспортированных строк по периодам: `168`.

Formula acceptance:

```text
Показатель: Оборот в кг
Период: 01.2026
Cached value: 593845
Export value: 593845 (numeric cell)
Formula text exported: NO
```

Проверены KPI:

- `Оборот в кг`;
- `Выручка за 1 кг`;
- `Итого расходов на 1 кг`;
- `Валовая прибыль на 1 кг`;
- `EBITDA`;
- `Операционная прибыль`.

## Tests и проверки

Добавлены обязательные unit-тесты:

- `test_kpi_context_from_department`;
- `test_kpi_cfo_resolution`;
- `test_kpi_month_value_from_formula_cell`;
- `test_kpi_export_mapping`.

Integration проходит цепочку `START_SERVICE → загрузка иерархии → загрузка БДР → KPI → организация/ЦФО → cached formula month value → Preview → Export XLSX → STOP_SERVICE` и проверяет `593845`.

```text
python -m pytest -q
199 passed, 6 skipped, 1 warning in 113.20s

python -m compileall -q src tests scripts
PASS

node --check src/excel_transform_1c/ui/static/run.js
PASS

git diff --check
PASS

git ls-files -- '*.xlsx'
empty
```

Единственное warning — существующий `StarletteDeprecationWarning` из `fastapi.testclient`.

## Smoke result

Отдельный HTTP process smoke выполнен на временном runtime с фактическим запуском и остановкой uvicorn:

```text
OWNER_SMOKE_HTTP_INITIAL_PASS
STOP_SERVICE PASS
OWNER_SMOKE_HTTP_POST_RESTART_PASS
STOP_SERVICE PASS
```

Проверены upload, диагностика, Preview, XLSX download и листы `OPIU Light`, `ОПИУ`, `Показатели` до и после restart.

Exact внешний файл `БДР 2026 ИТОГ.xlsx` не найден в профиле пользователя и на диске `C:`; в Git он не добавлялся. Формульный regression выполнен на структурном OOXML fixture с сохранённым cached result. Финальная проверка именно owner-файла остаётся Owner UX Smoke.

## Что сохранено

- `OrganizationHierarchyResolver` и ERP hierarchy код не изменялись.
- `Expense Resolver` не изменён.
- `Revenue Resolver` не изменён.
- Immutable RUN-local snapshot и single-flight/idempotency сохранены.
- Строки с отсутствующим cached result остаются видимыми с причиной и не исчезают молча.
- Реальные или тестовые `.xlsx` не добавлены в Git.
- Merge, release, push и PR не выполнялись.

## Feature Baseline result

- `CHANGED_AUTHORIZED`: `INPUT-004` — formula cell KPI получает только сохранённое вычисленное значение без Excel recalculation.
- `CHANGED_AUTHORIZED`: `RESULT-001`, `RESULT-002` — KPI-контекст и числовое значение сохраняются во всех трёх export-листах; `Показатели` разделяет строки по департаменту/ЦФО.
- `PRESERVED`: `MAP-001`–`MAP-005`, существующие Expense/Revenue resolvers, exact ERP hierarchy, `RUN-001`–`RUN-003`, `ERR-001`–`ERR-005`, три export-листа и `NO_LIVE_WRITE`.

## Риски и ограничения

- Сервис не вычисляет формулы. Если исходный Excel не содержит сохранённого cached result, KPI-значение остаётся незаполненным с диагностикой месячной ошибки.
- Exact owner-файл не был доступен как handoff input path; реальный Owner UX Smoke необходим для подтверждения его конкретного OOXML варианта.
- Расширение листа `Показатели` добавляет бизнес-колонки контекста перед существующими полями; потребители должны использовать заголовки, а не фиксированные номера колонок.

## Safety confirmation

```text
NO ADO
NO ODBC
NO 1C WRITE
NO LIVE WRITE
```

READY_FOR_OWNER_UX_SMOKE_BDR_KPI_VALUE
