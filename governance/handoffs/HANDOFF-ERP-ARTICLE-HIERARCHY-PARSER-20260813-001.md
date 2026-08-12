# Handoff — ERP article hierarchy parser

- Work ID: `WORK-ERP-ARTICLE-HIERARCHY-PARSER-20260813-001`
- Issue: `#8`
- Repository: `fitera2024-rgb/excel-transform-1c`
- Work branch: `fix/erp-article-hierarchy-parser`
- Target branch: `feat/v1-excel-transform-preview`
- Exact start base: `30f709ed2319d0ee8217f92d4f7f067e9fd3dc8e`
- Accepted product base: `e96fb403da7b96a5707ba131cb141788fe27bde3`
- Exact tested implementation head: `60bd84e7a6b5e116356539b026e92704faad72aa`
- Safety: `NO ADO / NO LIVE WRITE / NO MERGE`

## Что изменено

- ERP-код теперь связывается с ближайшим предшествующим официальным узлом иерархии.
- Непустая техническая аналитика в строке ERP-кода больше не заменяет официальную статью.
- Для ERP-выгрузки две единицы Excel `indent` детерминированно преобразуются в один уровень и сверяются с `outlineLevel` и текстовым отступом.
- Пропущенные, неподдерживаемые и противоречивые уровни завершают импорт понятной ошибкой вместо тихого исправления структуры.
- Повторяющиеся полные пути сохраняются как отдельные записи с уникальными кодами и остаются неоднозначными для exact mapper.

## Что сохранено

- Exact, case-sensitive full path остаётся единственным автоматическим правилом сопоставления.
- Fuzzy, typo, case-only и name-only autofix не добавлены.
- Ветки `Удалить` / `!!!Удалить` не скрываются и не исключаются.
- Структурное обнаружение не зависит от имени файла.
- Normal UI, protected/streaming upload flow, inline correction UX, ADO и write paths не менялись.
- Реальные ERP/бюджетные Excel и row-level extract в Git не добавлялись.

## Changed files

- `src/excel_transform_1c/adapters/references.py`
- `tests/helpers/workbooks.py`
- `tests/integration/test_reference_catalog_persistence.py`
- `tests/unit/test_erp_article_hierarchy_parser.py`
- `governance/handoffs/HANDOFF-ERP-ARTICLE-HIERARCHY-PARSER-20260813-001.md`

## Regression evidence

Синтетические fixtures покрывают:

- официальную статью в строке перед ERP-кодом;
- technical analytics `Счет затрат 26` в строке кода;
- `indent` 0/2/4 и соответствующий `outlineLevel` 0/1/2;
- соседние группы, которые остаются siblings;
- видимые `Удалить` / `!!!Удалить`;
- повторные full paths с разными ERP-кодами и видимую неоднозначность;
- 271 запись и 271 уникальный код;
- структурные аналоги исследовательских случаев `ЦБ-000239` и `00-000150` на вымышленных данных;
- явный отказ при нечётном `indent`, конфликте `indent`/`outlineLevel` и коде без предшествующего hierarchy node.

## Test results

Baseline до изменения:

- `python -m compileall -q src tests` — PASS.
- `python -m pytest -q` — `44 passed`, 1 external deprecation warning.

Exact tested implementation head `60bd84e7a6b5e116356539b026e92704faad72aa`:

- `python -m compileall -q src tests` — PASS.
- `python -m pytest tests/unit -q` — `21 passed`.
- `python -m pytest tests/integration -q` — `19 passed`.
- `python -m pytest tests/ui -q` — `11 passed`, 1 external Starlette/httpx deprecation warning.
- `python -m pytest -q` — `51 passed`, 1 external Starlette/httpx deprecation warning.
- `git diff --check` — PASS.
- `git ls-files '*.xlsx' '*.xls' '*.xlsm'` — PASS, no tracked Excel workbooks.

## Exact before/after

- Before: code-row analytics could enter the hierarchy stack; raw `indent` was compared directly with one-step `outlineLevel`; the research observed distorted name/path for 249 of 271 records.
- After: code-row analytics cannot replace the preceding official article; `indent=2` equals `outlineLevel=1`; synthetic regression preserves all 271 unique codes.
- Expected real-data diagnostic effect from research PR `#6`: exact mapping for 189/195 AY rows and 179/184 PV rows, 368/379 total. No real business workbook was executed or committed in this implementation task.

## Risks and limitations

- The accepted parser supports the documented ERP export structure. Odd indentation, conflicting structural signals, missing levels or a code before any official hierarchy node fail visibly and require source review.
- Real catalog reload and AY/PV verification remain coordinator/owner QA because real files are outside Git and no live/local catalog write was authorized here.
- CI status is recorded in the Draft PR after branch publication; local validation above is complete.

## Feature Baseline result

- `MAP-001`, `MAP-002`, `MAP-003`, `MAP-004`, `MAP-005`: `PRESERVED`.
- `REF-001`: `PRESERVED`.
- `INPUT-002`, `TRANS-001`, `UX-001`, `WRITE-001`, `GOV-001`: `PRESERVED`.
- All unrelated baseline IDs: `PRESERVED`.

Final delivery marker and exact delivery head are recorded in Draft PR and Issue `#8` after this handoff commit is published.

`READY_FOR_COORDINATOR_QA`
