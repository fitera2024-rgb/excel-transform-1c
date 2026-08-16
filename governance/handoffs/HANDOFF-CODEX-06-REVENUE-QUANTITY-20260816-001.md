# HANDOFF CODEX-06: Revenue + Quantity Indicators Engine

> **STATUS: READY_FOR_OWNER_UX_SMOKE_REVENUE_QUANTITY.** The coordinator gap report has been addressed. This handoff replaces the earlier `SUPERSEDED / CHANGES_REQUIRED` state.

## Git boundary

- Repository: `fitera2024-rgb/excel-transform-1c`
- Branch: `feat/final-owner-smoke-fitera-v2`
- Base SHA: `61c30fd2ed4a13c6bdb392bf2e614a7c40b60677`
- Final implementation SHA: `73cae073366900007eed473acaaa821b33f1507c`
- The handoff is committed separately so it can contain the immutable implementation SHA. The delivery HEAD is reported with the owner handoff.
- No merge, PR, release, push, ADO, ODBC, 1C write or live write was performed.

## Delivered behavior

- Added explicit indicator types `EXPENSE`, `REVENUE` and `QUANTITY`, including Preview labels `Расход`, `Доход` and `Количество`.
- Preserved the expense chain `группа раскрытия → статья → условия формулы → показатель`.
- Expense completeness and export are type-aware: `sales_channel` is not required for an exact expense result. The real owner expense range exports matched indicators with an empty channel.
- Revenue analytics are read only from the selected input-budget row: `Контрагент`, `ИНТ канал сбыта`/`Канал сбыта`, `Сеть`, `Регион продаж`, and `Номенклатура` when declared by a rule. No ERP counterparty card or enrichment query is used.
- `RevenueResolver` requires an exact group + article match, optional exact full path, and exact values for every constraint declared by the rule. A formula condition is compared only when the input row contains one.
- `QuantityResolver` requires exact nomenclature + unit, a present quantity value, and one exact catalog link.
- Missing required input is `Требует внимания`; mismatch is unresolved; multiple exact candidates are ambiguous. There is no fuzzy, `contains`, name-only, first-candidate or guessed fallback.
- Export sheet names and column structures remain unchanged: `OPIU Light`, `ОПИУ`, `Показатели`.

## Packaged rules and source coverage

- Total active classifier rules: **215**.
- `EXPENSE`: **208** exact packaged rules.
- `REVENUE`: **7** new exact packaged rules; derivation audit `7 candidates / 7 derived / 0 unresolved / 0 ambiguous`.
- `QUANTITY`: **0** packaged rules; source audit `7 candidates / 0 derived / 7 unresolved / 0 ambiguous`.
- The seven revenue rules cover the exact owner BDR articles `Опт`, `Розница`, `HoReCa`, `Сети ДВ`, `Сети Федеральные`, `Дискаунтеры ДВ`, and `Дискаунтеры Федеральные` under `Выручка_продажи внешние`.
- No supplied source contains an authoritative concrete `Номенклатура + Единица измерения → Показатель` pair. Quantity rows therefore remain `Требует внимания`; creating a rule by inference would violate the owner safety boundary.

Normalized read-only evidence packaged by the builder:

- 517 formula rows;
- 517 analytics rows;
- 310 MXL source selections;
- 683 report indicators;
- 22 regions;
- 233 networks.

The exact MXL evidence SHA-256 is `fa24195774e7e0d90f1aee523efccf2eb4b51f9c02540251034c54a2258c7864`.

## Real owner-budget smoke

Read-only workbook snapshot SHA-256: `9bc838a43ecc29f1b6d163264963c596a4edd7415f11587e2c52992cd66bd970`.

- Exact BDR summary detection found the owner range on `БДР 2026 ИТОГ` without selecting a first candidate.
- Revenue: 7 source rows expanded to 84 monthly records; all 7 indicators resolved automatically; input sales channels were preserved; ERP codes remained empty; exported indicator total reconciled to the selected input total.
- Expense: the separate real prepared expense range was selected explicitly; packaged exact matches were present; every matched expense had an empty `sales_channel`; the `Показатели` export retained those rows with an empty channel.
- Quantity without a proven packaged pair stayed `Требует внимания` and was not exported as a resolved indicator.
- The workbook also contains more than one structurally valid revenue/expense candidate. The application presents candidate selection; it does not silently combine ranges or take the first candidate.

The password-protected `source-original.xlsx` was not changed. Smoke used the application's existing decrypted working snapshot of the same upload because no workbook password was available.

## Verification

- `python -m compileall -q src tests scripts` — PASS.
- `python -m pytest -q` with both real source fixtures — PASS: `180 passed, 3 skipped, 1 warning`.
- Required resolver tests pass: `test_indicator_type_detection`, `test_revenue_resolver_exact_match`, `test_quantity_resolver_exact_match`, `test_expense_logic_not_changed`.
- `node --check src/excel_transform_1c/ui/static/run.js` — PASS.
- `git diff --check` — PASS; only configured LF/CRLF conversion warnings were emitted.
- Integration flow `START_SERVICE → Upload Excel → Load OPIU rules → Resolve expense/revenue/quantity → Preview → Confirm → Export XLSX → STOP_SERVICE` — PASS in the integration suite.
- Correctly marked offline package launcher smoke — PASS: health/home, initial HTTP owner workflow, export, stop, restart, persisted classifier, final stop.
- Service stop was verified after smoke.

## Offline package

- Build source SHA: `73cae073366900007eed473acaaa821b33f1507c`.
- ZIP: `EXCEL_TO_OPIU_LIGHT_USER_73cae0733669.zip`.
- Size: `8,149,027` bytes.
- SHA-256: `2165df75ae5094e3989335720d2358c170b5a4e7fa091068c57590d4c0bb2bdb`.
- The ZIP is a local handoff artifact only; it was not released or uploaded.

## Changed files from Base SHA

- Governance/package: `governance/handoffs/HANDOFF-CODEX-06-REVENUE-QUANTITY-20260816-001.md`, `governance/handoffs/REPORT-COORDINATOR-CODEX-06-GAP-20260816-001.md`, `packaging/user/README_USER_RU.md`.
- Builders/smoke: `scripts/build_opiu_baselines.py`, `scripts/owner_smoke_http.py`.
- Adapters/application: `src/excel_transform_1c/adapters/excel.py`, `persistence.py`, `references.py`, `src/excel_transform_1c/application/service.py`.
- Baselines: `src/excel_transform_1c/baselines/__init__.py`, `manifest.json`, `article_indicators.json`, `opiu_analytics.json`, `opiu_formulas.json`, `opiu_report_indicators.json`, `opiu_source_rules.json`, `regions.json`, `sales_networks.json`.
- Core/UI: `src/excel_transform_1c/core/__init__.py`, `detection.py`, `indicator_matching.py`, `indicator_resolvers.py`, `models.py`, `transform.py`, `src/excel_transform_1c/ui/templates/home.html`, `run.html`.
- Tests/helpers: `tests/helpers/workbooks.py`, `tests/integration/test_article_indicator_workflow.py`, `test_indicator_unresolved_rows.py`, `test_packaged_opiu_classifier_workflow.py`, `test_reference_catalog_persistence.py`, `test_revenue_quantity_workflow.py`, `tests/ui/test_indicator_unresolved_ui.py`, `test_ui_smoke.py`, `tests/unit/test_article_indicator_matching.py`, `test_input_revenue_analytics.py`, `test_packaged_opiu_baselines.py`, `test_real_revenue_baselines.py`, `test_revenue_quantity_resolvers.py`, `test_revenue_rule_import.py`.

## Limitations

- Quantity coverage cannot be made automatic until an authoritative source supplies exact nomenclature/unit/indicator links.
- Input ranges are selected independently. Automatic consolidation of separate expense and revenue ranges is outside the confirmed scope and is deliberately not inferred.
- The application does not query ADO/ODBC/1C and does not write to 1C or any live system in this implementation or smoke.
