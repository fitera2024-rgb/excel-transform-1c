# HANDOFF TASK-05B-03: Export reference columns

HANDOFF-ID: `HANDOFF-TASK-05B-03-EXPORT-REFERENCE-COLUMNS-20260816-001`

TASK-ID: `TASK-05B-03-EXPORT-REFERENCE-COLUMNS-20260816-001`

DATE: `2026-08-16`

BRANCH: `codex/task-05b-03-export-reference-columns`

BASE BRANCH: `codex/task-05b-02-erp-code-resolution`

BASE SHA: `2a2d6e0db1b914e7aa99fbc4c72b32cb2c7f073d`

FINAL IMPLEMENTATION SHA: `b8a8750ec83caf5103368c9a643f6bf2e2c072ad`

STATUS: `READY FOR EXPORT VERIFY / NO MERGE / NO LIVE WRITE`

`FINAL IMPLEMENTATION SHA` содержит код и тесты. Этот handoff и финальный marker добавляются отдельным documentation-only commit и не меняют проверенную реализацию.

## Что изменено

- Изменён только Excel-export adapter и связанные export expectations.
- На листах `OPIU Light` и `ОПИУ` отдельно выводятся:
  - `Организация`;
  - `Код организации`;
  - `Департамент`;
  - `Отдел`;
  - `ЦФО`;
  - `Код ЦФО`.
- `Организация` и `Код организации` берутся из exact root-полей resolver enrichment. Для старых записей без enrichment сохранён детерминированный fallback по внутреннему display-контракту `path (code)`.
- На агрегатном листе `Показатели` организация также разделена на `Организация` и `Код организации`; состав и суммы indicator aggregation не менялись.
- Коды организации и ЦФО записываются как текст, поэтому ведущие нули сохраняются.
- Экспорт отклоняет конфликтующие exact root-организации для одного агрегированного контекста вместо выбора первого результата.

## Acceptance result

| Поле | Значение |
|---|---|
| Организация | `4 Владивосток` |
| Код организации | `000000041` |
| Департамент | `Департамент обеспечения` |
| Отдел | `АЮ Отдел обеспечения` |
| ЦФО | `АЮ Отдел обеспечения` |
| Код ЦФО | `000000175` |

Проверены листы `OPIU Light`, `ОПИУ`, `Показатели`. Name и code не смешиваются в одной ячейке.

## Добавленные acceptance-тесты

- `test_export_organization_name_without_code`;
- `test_export_cfo_code_separate`;
- `test_export_root_organization_code`.

## Что сохранено

- Hierarchy reader и resolver не изменены.
- UI не изменён.
- Revenue и Quantity core/resolution/aggregation не изменены; обновлены только позиционные export assertions после добавления колонок.
- RUN/snapshot, source detection, preview, persistence и live-write boundary не изменены.
- Не добавлены `contains`, `startswith`, fuzzy, похожие названия или first-result fallback.
- ADO/ODBC/1C/DB write, live write, merge, release и PR не выполнялись.
- Реальные и тестовые `.xlsx` не добавлены в Git.

## Tests и checks

```text
python -m pytest -q
188 passed, 6 skipped, 1 warning

python -m pytest -q tests/integration/test_three_sheet_ado_export.py tests/integration/test_organization_reference_enrichment.py
7 passed

python -m compileall -q src tests scripts
PASS

node --check src/excel_transform_1c/ui/static/run.js
PASS

git diff --check
PASS

git ls-files -- '*.xlsx'
empty
```

Единственное warning — существующий `StarletteDeprecationWarning` из `fastapi.testclient`. Для полного прогона optional-поиск локального реального Инталев-файла был направлен на заведомо отсутствующий test-only путь: в пользовательском профиле присутствует недоступный junction `Documents/Bitrix24`, который ломает рекурсивный evidence scan вне репозитория.

## XLSX verification

- Из implementation-кода создана временная representative-книга вне Git.
- Artifact-tool импортировал и семантически проверил диапазоны `A1:V2`, `A1:R2`, `A1:I2` всех трёх листов.
- Значения кодов подтверждены как строки `000000041` и `000000175`.
- Formula error scan: empty.
- Все три листа отрендерены и визуально проверены; временные verification-файлы не входят в handoff.

## Feature Baseline result

- `CHANGED_AUTHORIZED`: `RESULT-001`, `RESULT-002` — task-authorized разнос reference name/code в Excel export.
- `PRESERVED`: `ORG-001`, `MAP-001`, `TRANS-001`, Revenue, Quantity, UI, immutable RUN-local snapshot, idempotency и `NO_LIVE_WRITE`.

## Риски и ограничения

- Позиции колонок export schema изменены по прямому требованию TASK-05B-03; внешним positional-consumers потребуется использовать новые заголовки/позиции.
- `Показатели` остаётся агрегатным листом и не получает детальные поля отдела/ЦФО; на нём разнесены только присутствующие в его контракте organization reference fields.
- Старый display fallback применяется только когда resolver enrichment отсутствует; он разбирает точный внутренний формат и не выполняет поиск по справочнику.
