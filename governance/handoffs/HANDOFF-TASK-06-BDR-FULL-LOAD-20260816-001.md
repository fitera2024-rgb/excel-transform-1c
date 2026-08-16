# HANDOFF TASK-06: Полная загрузка БДР

HANDOFF-ID: `HANDOFF-TASK-06-BDR-FULL-LOAD-20260816-001`

ASK-ID: `ASK-06-BDR-FULL-LOAD-20260816-001`

DATE: `2026-08-16`

BRANCH: `codex/task-06-bdr-full-load`

BASE BRANCH: `feat/final-owner-smoke-fitera-v2`

BASE SHA: `70d41c1a8a54cd2efec23639afa8805bae17c60e`

FINAL IMPLEMENTATION SHA: `a2534b9844e8aa86689af0f463019b50814bc0f8`

STATUS: `READY FOR OWNER UX SMOKE / NO MERGE / NO LIVE WRITE`

`FINAL IMPLEMENTATION SHA` содержит код и тесты. Этот handoff добавляется отдельным documentation-only commit и не меняет проверенную реализацию.

## Что изменено

- `БДР 2026 ИТОГ` представлен пользователю одним бизнес-источником. Внутренние подготовленные диапазоны этой книги не предлагаются как отдельные загрузки.
- Детектор находит полный БДР по структуре: непрерывным 12 месячным колонкам, строке `план` и упорядоченным точным якорям БДР. Имя файла, листа или диапазона не является основанием детекции.
- В одном RUN автоматически выделяются доходные, расходные и KPI-показатели.
- Добавлен тип показателя `KPI`; показатель БДР берётся из строки источника без ручного mapping.
- Для строк БДР используется exact-only разрешение сокращённого отдела в выбранной ветке `OrganizationHierarchyResolver` с подъёмом по `parent` до организации. `contains`, fuzzy и выбор первого результата не добавлены.
- В экспорт передаются `Организация`, `Код организации`, `Департамент`, `Отдел`, `ЦФО`, `Код ЦФО`, `Тип показателя`, `Показатель`, `Период`, `Значение`.
- Сохранены листы `OPIU Light`, `ОПИУ`, `Показатели`.
- Перед экспортом UI показывает прочитанные строки БДР, количество доходных/расходных/KPI/всех показателей, exact-сопоставления и экспортированные показатели/периодные строки.
- Для каждой исключённой строки сохраняется видимая причина; неоднозначная или отсутствующая exact-иерархия не проходит молча.
- Формулировка выбора заменена на `Выберите бизнес-источник`; служебный classifier для полного БДР не показывается.
- HTTP smoke переведён на полный БДР-поток и проверяет сохранение результата после перезапуска сервиса.

## Изменённые файлы

- `packaging/user/README_USER_RU.md`
- `scripts/owner_smoke_http.py`
- `src/excel_transform_1c/adapters/excel.py`
- `src/excel_transform_1c/application/service.py`
- `src/excel_transform_1c/core/detection.py`
- `src/excel_transform_1c/core/indicator_matching.py`
- `src/excel_transform_1c/core/indicator_resolvers.py`
- `src/excel_transform_1c/core/models.py`
- `src/excel_transform_1c/core/organization_hierarchy.py`
- `src/excel_transform_1c/core/transform.py`
- `src/excel_transform_1c/ui/app.py`
- `src/excel_transform_1c/ui/templates/blocked.html`
- `src/excel_transform_1c/ui/templates/choose_candidate.html`
- `src/excel_transform_1c/ui/templates/home.html`
- `src/excel_transform_1c/ui/templates/run.html`
- `tests/helpers/workbooks.py`
- `tests/integration/test_article_indicator_workflow.py`
- `tests/integration/test_bdr_full_load_workflow.py`
- `tests/integration/test_intalev_opiu_workflow.py`
- `tests/integration/test_packaged_opiu_classifier_workflow.py`
- `tests/integration/test_revenue_quantity_workflow.py`
- `tests/integration/test_three_sheet_ado_export.py`
- `tests/integration/test_workflow.py`
- `tests/ui/test_ui_smoke.py`
- `tests/unit/test_bdr_full_load.py`

## Unit и integration acceptance

Добавлены требуемые unit-тесты:

- `test_bdr_detect_income_block`;
- `test_bdr_detect_expense_block`;
- `test_bdr_detect_kpi_block`;
- `test_bdr_full_hierarchy_resolution`;
- `test_bdr_export_not_empty`.

Дополнительно проверена видимая причина исключения при отсутствии exact-совпадения. Integration-тест проходит цепочку `START_SERVICE -> upload hierarchy -> upload BDR -> detect blocks -> Preview -> confirm -> export XLSX -> STOP_SERVICE` через FastAPI lifecycle и проверяет модель данных и три export-листа.

## Tests и checks

```text
python -m pytest -q
195 passed, 6 skipped, 1 warning in 112.47s

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

## Smoke result и количество показателей

Representative БДР smoke содержит 14 показателей:

- доходные: `3`;
- расходные: `5`;
- KPI: `6`;
- всего показателей: `14`;
- exact-сопоставлено: `14`;
- экспортировано показателей: `14`;
- экспортировано месячных строк: `168`.

Результаты:

```text
development HTTP smoke initial: OWNER_SMOKE_HTTP_INITIAL_PASS
development HTTP smoke after restart: OWNER_SMOKE_HTTP_POST_RESTART_PASS
packaged HTTP smoke initial: OWNER_SMOKE_HTTP_INITIAL_PASS
packaged HTTP smoke after restart: OWNER_SMOKE_HTTP_POST_RESTART_PASS
packaged STOP_SERVICE verification: PACKAGE_STOP_SERVICE_PASS
```

Smoke проверяет загрузку exact-иерархии, один полный БДР, Preview, подтверждение, XLSX и листы `OPIU Light`, `ОПИУ`, `Показатели`. Повторный запуск меняет PID, сохраняет RUN и позволяет повторно скачать тот же экспорт.

## Package status

Пакет собран из `FINAL IMPLEMENTATION SHA`:

```text
EXCEL_TO_OPIU_LIGHT_USER_a2534b9844e8.zip
size: 8155012 bytes
sha256: 86f0a21488bacb2a50e045cfb6dc32ef50e4dfae5d54155ef9d7bd90cc42974f
ZIP integrity: PASS (33 entries)
PACKAGE_BUILD.txt commit: a2534b9844e8aa86689af0f463019b50814bc0f8
```

Локальный verification path (вне Git):

`C:\Users\NB-FIT\AppData\Local\Temp\codex-bdr-full-load-package-a2534b9\dist\EXCEL_TO_OPIU_LIGHT_USER_a2534b9844e8.zip`

## Что сохранено

- Существующий `ExpenseResolver` не изменён по поведению; полный БДР идёт своим прямым indicator-контрактом.
- Текущие ERP-подтверждения и остальные источники сохранены.
- RUN использует immutable RUN-local snapshot; один бизнес-клик не создаёт дублирующий RUN/write.
- Business Core не получил зависимости от UI, ADO connection objects или filesystem paths.
- ADO/ODBC/1С/DB write и live write не добавлялись и не выполнялись.
- Реальные и тестовые `.xlsx` не добавлены в Git.
- Merge, push и PR не выполнялись.

## Feature Baseline result

- `CHANGED_AUTHORIZED`: `INPUT-003`, `INPUT-005`, `INPUT-007` — task-authorized представление полного БДР единым бизнес-источником и структурное определение его внутренних блоков.
- `CHANGED_AUTHORIZED`: `RESULT-001`, `RESULT-002` — task-authorized добавление типа/названия показателя и значения в сохраняемые export-листы.
- `PRESERVED`: exact-only organization hierarchy, существующий Expense Resolver, ERP confirmations, остальные источники, immutable RUN-local snapshot, idempotency, три export-листа и `NO_LIVE_WRITE`.

## Риски и ограничения

- Реальный owner-файл `БДР 2026 ИТОГ.xlsx` не был предоставлен как exact handoff/input path. Автоматический и packaged smoke выполнены на структурно representative книге; финальная UX-проверка реального файла остаётся owner gate.
- Детектор намеренно требует точные структурные признаки и якоря. Книга с другой структурой будет отклонена с диагностикой, а не принята по похожему имени.
- При нескольких подходящих полных схемах или неоднозначном exact-сопоставлении организация/отдел результат блокируется; первый результат не выбирается.
- Показанные количества `14` и `168` относятся к representative smoke, а не к не предоставленному реальному финансовому файлу.

## Safety confirmation

```text
NO ADO
NO ODBC
NO 1C WRITE
NO LIVE WRITE
```
