# HANDOFF TASK-06-08: KPI-контекст и вычисленные месячные значения БДР

HANDOFF-ID: `HANDOFF-TASK-06-08-BDR-KPI-CONTEXT-VALUE-RESOLVER-20260816-001`

TASK-ID: `TASK-06-08-BDR-KPI-CONTEXT-VALUE-RESOLVER-20260816-001`

DATE: `2026-08-16`

BRANCH: `codex/task-06-08-bdr-kpi-context-value`

BASE SHA: `83c1f573c61cc0f0b086026bece02be8b0d66326`

CONTINUATION START SHA: `08a5618873976e97ac6d6e7e9c68ce0747ad8e8a`

FINAL IMPLEMENTATION SHA: `c6b7dcf608941608726c651461a3350446b716d3`

STATUS: `READY FOR OWNER UX SMOKE / DRAFT PR / NO MERGE / NO LIVE WRITE`

`FINAL IMPLEMENTATION SHA` — проверенный code commit. Этот handoff обновляется
отдельным documentation-only commit и не меняет проверенную реализацию.

## Что изменено

- Сохранён business-safe DTO `KPIResult`: организация и код, исходный отдел,
  наименование родительского департамента, ЦФО и код, тип/название KPI, период
  и числовое значение.
- Исправлен дефект реального owner-файла: department-aware БДР-grid и сохранённые
  вычисленные итоги KPI могут находиться на разных листах одной книги.
- Основным business candidate остаётся структурно доказанный grid с колонкой
  `Отдел`. Для значений к нему присоединяется ровно один summary того же года,
  найденный по структуре, а не по имени файла или листа.
- Связь `строка показателя × месяц` строится только по exact indicator label и
  exact month column. Для совпадающих координат приоритет имеет та же строка;
  для KPI-tail допускается только единственная exact-строка того же показателя.
- Адаптер читает сохранённый OOXML result `<v>` из формульной ячейки. Формула,
  текст формулы и ссылка на ячейку не становятся значением результата.
- Учтён числовой display precision исходного Excel: например, сохранённое
  дробное значение с форматом `#,##0` передаётся как показанное пользователю
  целое число.
- Агрегация листа `Показатели` сохраняет границы департамента/ЦФО и не объединяет
  одинаковый KPI разных организационных контекстов.
- Во всех трёх листах `OPIU Light`, `ОПИУ`, `Показатели` KPI содержит тип,
  показатель, период, числовое значение и доступный организационный контекст.
- Перед экспортом показываются счётчики `KPI найдено`, `KPI с организацией`,
  `KPI с периодом`, `KPI со значением`, `KPI экспортировано`, а также количество
  прочитанных месячных ячеек, числовых значений и ошибок Excel.

## Изменённые файлы

- `governance/handoffs/HANDOFF-TASK-06-08-BDR-KPI-CONTEXT-VALUE-RESOLVER-20260816-001.md`
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

## Реальный защищённый owner-file smoke

Файл открыт через normal HTTP upload с одноразовым вводом пароля. Пароль, файл и
его расшифрованная копия не добавлялись в Git и не записывались в handoff.

Диагностика перед экспортом:

```text
Прочитано строк БДР: 363
Месячных ячеек прочитано: 4356
Числовых значений: 4284
Ошибок Excel: 72
Строк требует внимания: 363
KPI найдено: 62
KPI с организацией: 62
KPI с периодом: 62
KPI со значением: 62
KPI экспортировано: 62
```

Контрольные значения за `01.2026` одинаково подтверждены в `OPIU Light`,
`ОПИУ` и `Показатели`:

```text
Оборот в кг: 593845
Выручка за 1 кг: 470
Итого расходов на 1 кг: 166
Валовая прибыль на 1 кг: 139
Выручка ИТОГО: 278827041
Валовая прибыль: 82400731
EBITDA: 18214892
Операционная прибыль: 3945151
```

Организация KPI: `4 Владивосток`; код организации: `000000041`. У агрегатных
KPI real-owner summary нет исходного `Отдел`, поэтому ложный отдел/ЦФО им не
назначается. При наличии source-proven `Отдел` его exact hierarchy traversal
проверен отдельными unit/integration fixtures.

Проверка всех месяцев:

```text
OPIU Light: 744 KPI period rows, 744 numeric, 0 formula text
ОПИУ:       744 KPI period rows, 744 numeric, 0 formula text
Показатели: 408 KPI period rows, 408 numeric, 0 formula text
Периоды: 01.2026 ... 12.2026
```

Оставшиеся `72` ошибки — сохранённые Excel errors в не-KPI исходных ячейках.
Они остаются видимыми в диагностике; все `62` KPI имеют значения и экспортированы.

## Tests и regression

Обязательные unit-тесты:

- `test_kpi_context_from_department`;
- `test_kpi_cfo_resolution`;
- `test_kpi_month_value_from_formula_cell`;
- `test_kpi_export_mapping`;
- split-sheet regression для exact summary indicator/month mapping.

```text
python -m pytest -q
200 passed, 6 skipped, 1 warning in 222.78s

python -m pytest -q tests/unit/test_bdr_kpi_context_value.py tests/unit/test_bdr_full_load.py
11 passed in 2.34s

python -m compileall -q src tests scripts
PASS

node --check src/excel_transform_1c/ui/static/run.js
PASS

git diff --check
PASS

Untracked/tracked task XLSX
NONE
```

Единственное warning — существующий `StarletteDeprecationWarning` из
`fastapi.testclient`.

## Windows offline package smoke

Пакет собран из `FINAL IMPLEMENTATION SHA` с полным локальным wheelhouse:

```text
EXCEL_TO_OPIU_LIGHT_USER_c6b7dcf60894.zip
SHA256: 941b3de6b4176478d68a873a673a6cc91c8237ab2226e09665114443eafa646d
ZIP integrity: PASS
PACKAGE_BUILD commit: c6b7dcf608941608726c651461a3350446b716d3
```

Проверен фактический packaged flow:

```text
START_SERVICE: PASS
HOME/HEALTH/imports: PASS
OWNER_SMOKE_HTTP_INITIAL_PASS
REAL_PROTECTED_PACKAGE_SMOKE_PASS
RESTART replaced PID: PASS
OWNER_SMOKE_HTTP_POST_RESTART_PASS
STOP_SERVICE: PASS
PORT RELEASE: PASS
```

## Что сохранено

- `OrganizationHierarchyResolver` и ERP hierarchy код не изменялись.
- `Expense Resolver` не изменён.
- `Revenue Resolver` не изменён.
- Immutable RUN-local snapshot и single-flight/idempotency сохранены.
- Вход определяется по структуре/схеме, а не по имени файла или листа.
- Строки без сохранённого cached result остаются видимыми с причиной.
- Реальные и тестовые `.xlsx` не добавлены в Git.
- Merge, release, ADO, ODBC и любые live writes не выполнялись.

## Feature Baseline result

- `CHANGED_AUTHORIZED`: `INPUT-004` — formula cell KPI получает только
  сохранённое вычисленное значение без Excel recalculation.
- `CHANGED_AUTHORIZED`: `RESULT-001`, `RESULT-002` — KPI-контекст и числовое
  значение сохраняются во всех трёх export-листах; `Показатели` разделяет строки
  по доступному source-proven организационному контексту.
- `PRESERVED`: `MAP-001`–`MAP-005`, существующие Expense/Revenue resolvers,
  exact ERP hierarchy, `RUN-001`–`RUN-003`, `ERR-001`–`ERR-005`, три export-листа
  и `NO_LIVE_WRITE`.

## Риски и ограничения

- Сервис не вычисляет формулы самостоятельно. Если Excel не сохранил cached
  result, ячейка остаётся незаполненной с явной диагностикой.
- У агрегатного KPI без source-proven `Отдел` нельзя безопасно вывести ЦФО;
  выбранная организация run сохраняется, а ложный hierarchy context не создаётся.
- Лист `Показатели` содержит бизнес-колонки контекста; потребители должны
  использовать заголовки, а не фиксированные номера колонок.

## Safety confirmation

```text
NO MERGE
NO ADO
NO ODBC
NO 1C WRITE
NO LIVE WRITE
```

READY_FOR_OWNER_UX_SMOKE_REAL_BDR
