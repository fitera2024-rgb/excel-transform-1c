# HANDOFF CODEX-06: Revenue and Quantity Indicator Engine

## Git boundary

- Repository: `fitera2024-rgb/excel-transform-1c`
- Branch: `feat/final-owner-smoke-fitera-v2`
- Base SHA: `61c30fd2ed4a13c6bdb392bf2e614a7c40b60677`
- Final SHA (implementation): `e306d89c4ed68addb42fbf164d3dd4ebef720d9a`
- The handoff is committed separately so the document can contain the immutable implementation SHA.
- Merge, release, PR, ADO, ODBC, 1C write and live write were not performed.

## What changed

- Added explicit indicator classification: `EXPENSE`, `REVENUE`, `QUANTITY`.
- Every classifier rule and every Preview record now has an indicator type.
- Added exact structural input fields for revenue and quantity without making them required for legacy prepared-budget inputs.
- Added type labels to Preview: `Расход`, `Доход`, `Количество`.
- Missing, incomplete or ambiguous revenue/quantity links remain `Требует внимания`.
- Kept the export contract unchanged: sheets `OPIU Light`, `ОПИУ`, `Показатели` and their existing columns.

## Resolver boundary

- `ExpenseResolver` is an alias of the existing `ExactArticleIndicatorMatcher`.
- `src/excel_transform_1c/core/indicator_matching.py` was not modified.
- `RevenueResolver` uses one exact key: group of revenue + article + formula condition + analytics. It does not use fuzzy, contains, title-only matching or first-result selection.
- `QuantityResolver` requires quantity in the source row, nomenclature, unit and one exact nomenclature/unit link to an indicator.
- `IndicatorResolverEngine` routes each Preview record to exactly one resolver by its explicit/structurally detected type.

## Source evidence used

The supplied workbooks and MXL were inspected read-only; source files were not changed or added to Git:

- `ОПИУ ФОРМУЛЫ.xlsx`
- `ОПИУ аНАЛИТИКИ.xlsx`
- `Источники для ОПИУ_ ЕРП.mxl`
- `ПоказателиОтчетов_ОПИУ_ЕРП.xlsx`
- `Регионы.xlsx`
- `СЕТИ.xlsx`

Observed evidence used in the resolver contract:

- formula and analytics rows align by the same exact business-row sequence;
- the MXL supplies exact source/formula relationships for only part of the formula references;
- the indicator catalog does not provide a filled, authoritative type value;
- therefore type and resolution are structural and exact, and uncovered links are not guessed.

## Changed implementation files

- `src/excel_transform_1c/adapters/references.py`
- `src/excel_transform_1c/application/service.py`
- `src/excel_transform_1c/core/__init__.py`
- `src/excel_transform_1c/core/detection.py`
- `src/excel_transform_1c/core/indicator_resolvers.py`
- `src/excel_transform_1c/core/models.py`
- `src/excel_transform_1c/core/transform.py`
- `src/excel_transform_1c/ui/templates/run.html`
- `tests/helpers/workbooks.py`
- `tests/integration/test_article_indicator_workflow.py`
- `tests/integration/test_revenue_quantity_workflow.py`
- `tests/unit/test_revenue_quantity_resolvers.py`

## Tests

Added unit coverage:

- `test_indicator_type_detection`
- `test_revenue_resolver_exact_match`
- `test_quantity_resolver_exact_match`
- `test_expense_logic_not_changed`

Added integration coverage for:

- service lifespan start/stop;
- Excel upload;
- classifier/rules upload;
- expense, revenue and quantity detection;
- Preview values and user-facing type labels;
- confirmation;
- XLSX export with all three indicator types and unchanged sheet/header contracts.

## Verification and smoke result

- `python -m compileall -q src tests scripts` — PASS
- `python -m pytest -q` — PASS: `148 passed, 5 skipped, 1 warning`
- `node --check src/excel_transform_1c/ui/static/run.js` — PASS
- `git diff --check` — PASS
- Revenue/quantity integration smoke (`START_SERVICE → upload Excel → upload rules → detect three types → Preview → Confirm → Export XLSX → STOP_SERVICE`) — PASS

The first full pytest attempt encountered an unrelated Windows environment error while an optional real-file test recursively inspected the unavailable `Documents\Bitrix24` path. The successful required run set that optional real-file fixture to an explicitly absent path, causing the test's intended `skip`; no production or test code was changed to mask the environment issue.

## Feature Baseline result

PASS. Existing CFO, organizational-unit, ERP-code, bulk-confirmation, expense-resolution and three-sheet export tests remain green. The existing expense matcher and export columns are unchanged.

## Limitations

- The resolver accepts only complete exact keys; it deliberately does not normalize case, use fuzzy/contains matching or select the first candidate.
- Supplied MXL evidence covers only part of the referenced formula vocabulary. Relationships absent from that evidence require an explicit classifier row and otherwise remain `Требует внимания`.
- A quantity without an explicit unit or nomenclature-to-indicator link remains `Требует внимания`.
- The supplied real source workbooks/MXL are evidence inputs and are not persisted in the repository or exposed as technical content in normal UI.
