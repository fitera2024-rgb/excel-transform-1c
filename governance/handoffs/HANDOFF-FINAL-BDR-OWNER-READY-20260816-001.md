# Handoff — полный БДР: source reconciliation и owner-ready package

## Идентификация

- WORK-ID: `WORK-FINAL-BDR-OWNER-READY-20260816-001`.
- TASK: `TASK-06-08-BDR-KPI-CONTEXT-VALUE-RESOLVER-20260816-001`.
- Ветка: `codex/task-06-08-bdr-kpi-context-value`.
- Исходный base задачи: `83c1f573c61cc0f0b086026bece02be8b0d66326`.
- Base продолжения/finalization: `45d514eba1a48efa8f09316ec00de792936e6359`.
- Exact implementation и локально проверенный package head: `7b6615a862a92e7fa3b367cb0e849b4111d521e1`.
- Draft PR: `#25`.

Governance-коммит, содержащий этот handoff, не меняет application/package source. Его exact delivery SHA фиксируется в Draft PR #25 и финальном сообщении: SHA коммита невозможно самореферентно записать в содержимое этого же коммита.

## Результат

Сервис структурно выбирает один полный БДР и преобразует KPI, доходы и расходы в один результат без зависимости KPI от статьи расходов. Исправлены:

- точная связь `показатель × месяц` с сохранённым вычисленным значением Excel;
- помесячное чтение из отдельного сохранённого value-sheet при наличии формул на planning-sheet;
- чтение подготовленных expense/income диапазонов как компонентов одного БДР;
- организационный контекст KPI через точный отдел и существующий `OrganizationHierarchyResolver`;
- отдел, департамент, ЦФО, код ЦФО, организация и код организации;
- сохранение аналитики `Канал сбыта` в `OPIU Light`, `ОПИУ`, `Показатели`;
- точная Excel-строка/ячейка в preview и экспорте при сохранении отдельного RUN-local identity;
- массовое подтверждение строк composite-БДР после разделения RUN id и видимого Excel row;
- структурное чтение одногомесячного и годового Intalev ОПИУ;
- source display precision для процентов и числовых component cells;
- owner/package smoke, использующий канонические export headers вместо хрупких номеров колонок.

Не менялись бизнес-правила Expense Resolver и Revenue Resolver, live-write, 1С, ADO/ODBC интеграции и UI массовых подтверждений за пределами исправления корректной идентичности строки.

## Реальные источники

Все owner `.xlsx`/`.mxl` использовались только как внешние immutable snapshots. `git ls-files '*.xls' '*.xlsx' '*.xlsm' '*.xlsb'` возвращает пустой результат.

Структурная обработка:

- АЮ БДР: 343 показателя; KPI 62, доходы 86, расходы 195; 4 116 периодов, 4 104 числовых значения, 12 исходных Excel-ошибок;
- ПВ БДР: 335 показателей; KPI 62, доходы 89, расходы 184; 4 020 периодов, 3 964 числовых значения, 12 исходных Excel-ошибок;
- ПС БДР: 266 показателей; KPI 52, доходы 35, расходы 179; 3 192 периода, 2 739 числовых значений, 372 исходные Excel-ошибки;
- годовой Intalev ОПИУ: 475 показателей / 5 700 числовых периодов;
- месячный Intalev ОПИУ: 180 показателей / 180 числовых значений за январь.

Справочники статей, организаций, аналитик, формул, регионов, сетей, видов отчётов, периодов, показателей, сценариев и табличных данных были проверены как exact owner inputs/reference inventory. MXL использован только как read-only reference evidence.

## Независимая source reconciliation — АЮ

Проверка независимо читает cached result owner-книги и сопоставляет его с выгрузкой по точному ключу `лист + строка + показатель + месяц + организационный контекст + канал`.

- source facts: **4 104**;
- output facts: **4 104**;
- exact matches: **4 104**;
- Missing Output: **0**;
- Extra Output: **0**;
- Value Mismatch: **0**;
- Context Mismatch: **0**;
- indicator rollup mismatches: **0**;
- formula text values в результате: **0**;
- service defects remaining: **0**;
- исходные Excel errors: **12**;
- Attention: **244** уникальные source rows / **2 928** period rows;
- unresolved source/reference gaps: **243**.

Контроли января 2026 совпали на всех трёх листах:

- Оборот в кг: `593845`;
- Выручка за 1 кг: `470`;
- Итого расходов на 1 кг: `166`;
- Валовая прибыль на 1 кг: `139`;
- Выручка ИТОГО: `278827041`;
- Валовая прибыль: `82400731`;
- EBITDA: `18214892`;
- Операционная прибыль: `3945151`.

Внешний отчёт, не добавленный в Git:

- `C:\Users\NB-FIT\AppData\Local\Temp\fitera-final-bdr-88d5c42ef3334a6c9a3a69b06abda87c\artifacts\BDR_SOURCE_RECONCILIATION_REPORT.xlsx`;
- SHA-256: `8b10f9fca472792f6624aa888d3b9baea5e28df4a6939187fdcbe3170fddd354`;
- листы: `Summary`, `Indicator_Month_Reconciliation`, `Missing_Output`, `Extra_Output`, `Value_Mismatch`, `Context_Mismatch`, `Excel_Errors`, `Attention`.

## KPI

Для АЮ обработано **62 KPI-показателя / 744 помесячных KPI-записи**. Диагностика реального HTTP RUN:

- KPI найдено: 62;
- KPI с организацией: 62;
- KPI с периодом: 62;
- KPI со значением: 62;
- KPI экспортировано: 62.

В `OPIU Light`, `ОПИУ`, `Показатели` присутствуют тип показателя, показатель, период, числовое значение, отдел, ЦФО и код ЦФО. Формулы и их текст в поле `Значение` не передаются.

## Tests

Exact implementation head `7b6615a862a92e7fa3b367cb0e849b4111d521e1`:

- `python -m pytest -q`: **208 passed, 6 skipped**;
- focused confirmation/UI regression: **37 passed**;
- `python -m compileall -q src tests scripts`: PASS;
- `node --check src/excel_transform_1c/ui/static/run.js`: PASS;
- `git diff --check`: PASS.

Добавлено/расширено покрытие KPI context/CFO/formula value/export, full BDR components и channel blocks, display precision, exact source coordinates, confirmation identity, optional income context, одно- и двенадцатимесячного Intalev.

## Реальный HTTP owner smoke

Source service, initial:

- `/health`, upload, structural detection, preview и export: PASS;
- 343 показателя / 4 116 месячных ячеек / 4 104 числа;
- 12 исходных Excel errors;
- явное HTTP-подтверждение `Налогообложение не требуется`: 28 строк, PASS;
- `OPIU Light`: 4 116 data rows;
- `ОПИУ`: 4 116 data rows;
- `Показатели`: 1 680 data rows;
- formula text values: 0.

После STOP/START на том же runtime:

- health и baseline/reference state: PASS;
- повторный owner upload/preview/export: PASS;
- те же диагностические счётчики и контрольные значения: PASS;
- порт `18765` освобождён после финального STOP: PASS.

## Offline Windows package

- Package source head: `7b6615a862a92e7fa3b367cb0e849b4111d521e1`.
- ZIP: `C:\Users\NB-FIT\AppData\Local\Temp\fitera-final-bdr-88d5c42ef3334a6c9a3a69b06abda87c\package-7b6615a862a9\dist\EXCEL_TO_OPIU_LIGHT_USER_7b6615a862a9.zip`.
- SHA-256: `b50cbb0eefc12fc72850bfc3cc93c0406f39074e0436fe647cdeaa856d0ad98f`.
- Размер: 8 162 702 bytes.
- wheelhouse install без сети: PASS;
- packaged launcher initial/restart: PASS;
- packaged synthetic HTTP owner smoke initial/post-restart: PASS;
- packaged real АЮ owner-file smoke initial/post-restart: PASS;
- packaged real export: 4 116 / 4 116 / 1 680 data rows, formula text values 0;
- `STOP_SERVICE`: PASS;
- port `18766` released: PASS;
- ZIP integrity: PASS.

## Изменённые Git-visible файлы

- `.github/workflows/final-owner-smoke-package-v2.yml`;
- `scripts/owner_smoke_http.py`;
- `src/excel_transform_1c/adapters/excel.py`;
- `src/excel_transform_1c/application/service.py`;
- `src/excel_transform_1c/core/detection.py`;
- `src/excel_transform_1c/core/models.py`;
- `src/excel_transform_1c/core/transform.py`;
- `src/excel_transform_1c/ui/templates/run.html`;
- `tests/integration/test_article_indicator_workflow.py`;
- `tests/integration/test_bdr_full_load_workflow.py`;
- `tests/integration/test_indicator_unresolved_rows.py`;
- `tests/integration/test_intalev_opiu_workflow.py`;
- `tests/integration/test_three_sheet_ado_export.py`;
- `tests/integration/test_workflow.py`;
- `tests/unit/test_bdr_full_load.py`;
- `tests/unit/test_bdr_kpi_context_value.py`;
- `tests/unit/test_input_revenue_analytics.py`;
- `tests/unit/test_intalev_opiu.py`;
- `governance/handoffs/HANDOFF-FINAL-BDR-OWNER-READY-20260816-001.md`.

## Feature Baseline result и ограничения

Результат: **PASS** — Excel → validation → transformation → preview → XLSX export остаётся простым локальным конвертером. Нет тихой потери числовых фактов; source errors и reference gaps остаются видимыми в диагностике и отчёте.

Оставшиеся 12 Excel errors и 243 source/reference gaps относятся к исходной книге/справочникам, а не к дефекту преобразования. Они не скрыты и не заменены догадками.

## Safety

- NO MERGE.
- NO RELEASE.
- NO ADO.
- NO ODBC.
- NO 1C WRITE.
- NO LIVE WRITE.
- NO SQL/live database write.
