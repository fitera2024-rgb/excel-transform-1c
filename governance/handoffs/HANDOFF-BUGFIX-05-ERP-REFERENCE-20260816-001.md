# HANDOFF BUGFIX-05: ERP reference enrichment и массовые подтверждения

HANDOFF-ID: `HANDOFF-BUGFIX-05-ERP-REFERENCE-20260816-001`

DATE: `2026-08-16`

REPOSITORY: `fitera2024-rgb/excel-transform-1c`

BRANCH: `feat/final-owner-smoke-fitera-v2`

BASE SHA: `b712cadba6d035108c56dcc9746ff42443c3b07c`

FINAL IMPLEMENTATION SHA: `5a2c8f6405f87ed6c1d26c0be2ec8be5dfecff3c`

STATUS: `READY FOR OWNER UX SMOKE`

`FINAL IMPLEMENTATION SHA` — exact commit с кодом и тестами. Handoff добавлен отдельным documentation-only commit, поэтому delivery HEAD на один commit новее и не меняет проверенную реализацию.

## Что изменено

- Добавлен exact-only resolver организационной ERP-иерархии `Организационная единица → Отдел → ЦФО`.
- Реальный parser `ОрганизациииерархияЕРП.xlsx` сохраняет точные поля `Головная организация`, `Верхний уровень иерархии` и код элемента.
- Enrichment использует только точные значения выбранной организационной единицы и исходного департамента; неоднозначность или отсутствие точного совпадения закрываются без догадки.
- Строка exact ERP-элемента без кода сохраняется parser-ом и получает статус `Требует внимания` с причиной `В ERP-справочнике отсутствует код элемента`.
- ADO-экспорт `ОПИУ` заполняет `Код Организационных единиц` и `Код ЦФО`; точное ERP-наименование ЦФО сохраняется и после штатного CFO-confirm.
- Исправлен ранний вызов `refreshBulkConfirmation()` до инициализации `const`-элементов ERP mass-confirm в `run.js`. ERP, Tax и CFO checkbox теперь переводят кнопку из `disabled` в enabled и позволяют выполнить `Применить всё`.
- Добавлены unit, integration и UI/Node DOM tests, включая все имена тестов из BUGFIX-05.

## Что сохранено

- Бизнес-логика и legacy-схема `OPIU Light` не изменены.
- Нет fuzzy/contains/partial/case-folded matching, сокращения `АЮ`, выбора первого кандидата или ручных таблиц соответствий.
- Структурное распознавание входа, immutable RUN-local snapshot и идемпотентность одного бизнес-клика сохранены.
- Normal UI не показывает SHA, internal paths, proof JSON или technical blocker codes.
- ADO, ODBC, 1C write, live write, merge, release, PR и CODEX-06 не выполнялись.
- `ОрганизациииерархияЕРП.xlsx` использован только read-only для теста и не добавлен в Git.

## Изменённые файлы

- `src/excel_transform_1c/adapters/excel.py`
- `src/excel_transform_1c/adapters/references.py`
- `src/excel_transform_1c/application/service.py`
- `src/excel_transform_1c/core/models.py`
- `src/excel_transform_1c/core/organization_hierarchy.py`
- `src/excel_transform_1c/ui/static/run.js`
- `tests/helpers/workbooks.py`
- `tests/integration/test_organization_reference_enrichment.py`
- `tests/ui/run_js_checkbox_harness.cjs`
- `tests/ui/test_bulk_erp_confirmation.py`
- `tests/ui/test_run_js_checkbox.py`
- `tests/ui/test_source_cfo_mapping_ui.py`
- `tests/ui/test_ui_smoke.py`
- `tests/unit/test_organization_hierarchy.py`
- `governance/handoffs/HANDOFF-BUGFIX-05-ERP-REFERENCE-20260816-001.md`

## Тесты и checks

Обязательный финальный прогон:

```text
python -m compileall -q src tests scripts                         PASS
python -m pytest -q                                              143 passed, 5 skipped, 1 warning
node --check src/excel_transform_1c/ui/static/run.js              PASS
git diff --check                                                 PASS
```

Для необязательного real-Intalev evidence test был явно задан несуществующий безопасный exact path через `EXCEL_INTAKE_REAL_OPIU_FILE`; это обходит рекурсивный обход недоступной локальной папки `Bitrix24` и переводит optional test в предусмотренный `skip`. Единственное warning — существующий `StarletteDeprecationWarning` из `fastapi.testclient`.

Проверены требуемые тесты:

- `test_cfo_code_resolution`
- `test_org_unit_code_resolution`
- `test_checkbox_enables_confirm_button`
- `test_bulk_confirm_erp`
- `test_bulk_confirm_tax`
- `test_bulk_confirm_cfo`

## Smoke result

`PASS` — packaged local flow выполнен на изолированном runtime и порту `8891`:

```text
START_SERVICE
upload ERP references and budget Excel
ERP preview
ERP bulk confirm
Tax bulk confirm
CFO bulk confirm
export XLSX
STOP_SERVICE
```

Browser DOM evidence для каждого массового действия:

```text
checkbox.checked = true
button.disabled = false
Применить всё = success
console errors = 0
```

Экспортированная строка `ОПИУ` после всех подтверждений:

```text
Организационная единица: ООО "Айс Юнион"
Код организационной единицы: 000000001
ЦФО: АЮ Административный Отдел
Код ЦФО: 000000173
```

Реальный test-only справочник:

```text
file: ОрганизациииерархияЕРП.xlsx
SHA-256: 3342603C0782FE12871AD55E7E19E778A97651E8CFF2E00F0CE6774295C57522
parsed nodes: 357
exact resolver: PASS
```

После последнего parser edge-case изменения exact implementation SHA повторно прошёл полный automated suite и read-only разбор реального справочника с тем же результатом.

## Feature Baseline result

`PRESERVED` для всех не относящихся к BUGFIX-05 возможностей. Изменены только разрешённые task scope: exact ERP organization enrichment, экспорт двух кодов, missing-code attention и работа трёх mass-confirm controls.

## Риски и ограничения

- Resolver намеренно не заполняет ERP-поля при отсутствии одного точного кандидата по выбранной организационной единице и департаменту.
- При нескольких точных кандидатах допускается только дополнительное точное равенство исходного ЦФО; иначе результат не выбирается.
- Строки без exact enrichment остаются с прежним бизнес-результатом и пустыми новыми кодами; данные не отбрасываются.
- Protected owner budget не использовался: integration smoke выполнен на синтетическом бюджетном XLSX и реальном test-only ERP-справочнике.
