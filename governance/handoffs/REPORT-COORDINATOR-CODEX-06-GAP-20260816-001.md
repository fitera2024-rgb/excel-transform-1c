# Coordinator report: CODEX-06 revenue/quantity gap

## Status

`CHANGES_REQUIRED / RELEASE_NOT_READY`

- Repository: `fitera2024-rgb/excel-transform-1c`
- Branch: `feat/final-owner-smoke-fitera-v2`
- Base SHA: `61c30fd2ed4a13c6bdb392bf2e614a7c40b60677`
- Audited HEAD before this report: `172c4715ee58299575b12d658712240a3398314c`
- The ZIP built from that HEAD must not be treated as the final CODEX-06 owner-smoke release.

## Owner clarification

The service transforms the uploaded budget into another representation of the same report. It must use the business fields already present in the input budget; it must not enrich revenue rows by reading an ERP counterparty card.

Type-specific chains:

- `EXPENSE`: disclosure group -> article -> formula conditions -> expense indicator. `Канал сбыта` is not required and must not be requested.
- `REVENUE`: revenue group/article + formula conditions + the applicable analytics present in the same input row (`Контрагент`, `ИНТ канал сбыта`, `Сеть`, `Регион продаж`, and `Номенклатура` when present) -> revenue indicator.
- `QUANTITY`: nomenclature -> unit -> quantity present -> quantity indicator.

All matching remains exact and structural. No fuzzy, contains, title-only guess or first candidate is allowed. If a field required by the applicable exact rule is absent from the input row, that row remains `Требует внимания`.

## Audited implementation facts

- Resolver classes and indicator type enum exist.
- Packaged source catalogs exist: 517 formulas, 517 analytics rows, 683 report indicators, 310 MXL source rules, 22 regions and 233 networks.
- Active packaged classifier rules: 208 total, all `EXPENSE`.
- Active packaged `REVENUE` rules: 0.
- Active packaged `QUANTITY` rules: 0.
- All 208 expense rules intentionally have an empty `sales_channel`.
- Shared result finalization currently marks a rule incomplete when `sales_channel` is empty, including expense rules.
- Preview guidance also prompts for a sales channel whenever an indicator exists without one, without limiting that action to revenue.
- The input model/parser has dedicated fields for revenue group, formula condition, generic analytics, nomenclature and unit, but no dedicated structural fields for counterparty, input sales channel, network and sales region.

## Consequences

- Existing expense behavior is not preserved: an exact packaged expense link can be shown but remains attention-only solely because a revenue analytic is absent.
- Revenue and quantity resolver unit/integration tests prove synthetic engine behavior only; they do not prove real packaged mappings.
- The supplied formula, analytics, MXL and indicator catalogs are packaged as source data, but they have not been compiled into active real revenue/quantity rules.
- The previous owner-ready marker and release ZIP are withdrawn.

## Required CODEX-06 correction

1. Make rule completeness and export requirements type-aware: `sales_channel` must never be required for `EXPENSE`.
2. Structurally detect and carry the relevant revenue analytics from the uploaded budget row: counterparty, sales channel, network, sales region and nomenclature when present.
3. Extend the exact revenue key only with analytics required by the corresponding formula/rule; do not invent values and do not query ERP.
4. Compile real `REVENUE` mappings from formulas + analytics + MXL source selections + report-indicator catalog.
5. Compile `QUANTITY` mappings only where the input contains nomenclature, unit and quantity and the source catalogs prove one exact indicator link.
6. Add real-input integration tests for all three types, including an exact expense match/export with an empty sales channel.
7. Re-run compileall, full pytest, JavaScript syntax check, diff check, service smoke and rebuild the Windows ZIP only after those checks pass.

## Verification truth

The recorded suite result (`152 passed, 5 skipped, 1 warning`) remains evidence that the current code is internally consistent with its tests. It is not evidence that the owner-confirmed revenue/quantity transformation is complete.

No merge, PR, release publication, ADO, ODBC, 1C write or live write is authorized by this report.
