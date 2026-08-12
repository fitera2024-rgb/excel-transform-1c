# Handoff — Inline attention correction and ERP hierarchy selector

- Status: `READY_FOR_COORDINATOR_QA`
- CR: `CR-INLINE-ATTENTION-ERP-TREE-20260813-001`
- Issue: `#9`
- Work branch: `feat/inline-attention-erp-tree`
- Target branch: `feat/v1-excel-transform-preview`
- Exact start head: `e54ebc6a498f42f504fe5f6cb98353b8b09e753a`
- Exact implementation head: `ee0a2a1ad3dc6aa1ce23eb903736f58893aa5d47`
- Safety: `NO ADO / NO LIVE WRITE / NO MERGE`

The final delivery head also contains this handoff file and is recorded in the
Draft PR and Issue marker. The implementation head above is the exact tested
code-and-tests commit.

## Changed

- Removed the standalone source-row selector from the preview page.
- Grouped unresolved issues by exact source Excel row and rendered one inline
  editor for each row, independent of its twelve monthly records.
- Added business context before each editor: source path, current ERP mapping,
  issue reasons, exact sheet/cell pointers, secondary source-row reference and
  all affected months.
- Added the catalog-only cascade `Тип расходов → Группа расходов → Статья →
  ERP-код`.
- The final selection displays the complete path, code and official ERP name.
- A unique remaining code is preselected in the browser but is not submitted
  until the user explicitly checks the confirmation control and submits the
  row form.
- Kept the existing corrections for tax, department, CFO, expense group and
  source article inside the same source-row context.
- Added JavaScript package-data inclusion and UI regression coverage.

## Preserved

- Existing POST correction workflow and reusable manual-mapping key.
- One correction updates every monthly record derived from the source row
  without rerunning the workbook.
- Other unresolved fields on the same source row remain visible after a partial
  correction.
- Organization hierarchy, open access to all organization nodes, scenario
  selector, `Весь год` default, maximum-completeness preview and OPIU Light
  export.
- Exact-first mapping semantics; no fuzzy, typo, case-insensitive or name-only
  automatic assignment.
- `Удалить` / `!!!Удалить` catalog entries remain present.

## Files

- `pyproject.toml`
- `src/excel_transform_1c/ui/templates/run.html`
- `src/excel_transform_1c/ui/static/app.css`
- `src/excel_transform_1c/ui/static/run.js`
- `tests/ui/test_ui_smoke.py`
- `governance/handoffs/HANDOFF-INLINE-ATTENTION-ERP-TREE-20260813-001.md`

Not changed:

- `src/excel_transform_1c/ui/app.py`
- `src/excel_transform_1c/application/service.py`
- ERP reference parser
- protected/streaming Excel adapter
- Business Core financial mapping semantics

No `CROSS_STREAM_DEPENDENCY` was required.

## Validation

- Targeted UI regression: `14 passed`.
- Full local regression: `47 passed`.
- JavaScript syntax: `node --check src/excel_transform_1c/ui/static/run.js` — PASS.
- Patch hygiene: `git diff --check` — PASS.
- Console errors during browser smoke: none.
- GitHub CI: pending Draft PR run at handoff creation.

## HTML and interactive evidence

Synthetic browser smoke used one source row with two simultaneous issues:

- rendered editor count: `1`;
- visible reasons: missing department and missing exact ERP mapping;
- exact pointers: `Произвольное имя!C3` and `Произвольное имя!H3`;
- affected months: January through December;
- selected path: `Административные → Связь → Интернет → ERP-001 · Интернет ERP`;
- unique-code preselection before confirmation: visible `ERP-001`, submitted
  hidden value empty, confirmation unchecked;
- after explicit confirmation: submitted code `ERP-001`;
- after correction: all `12/12` records of source row 3 contain `ERP-001`;
- remaining unresolved issue: `Не заполнено поле: департамент`;
- rerun counter remains `0`.

## Feature Baseline result

- `PREVIEW-003`, `UX-003`, `MAP-001..005`: `CHANGED_AUTHORIZED` by Issue #9
  and the Task Contract.
- `ORG-001..004`, `PERIOD-001..002`, `SCENARIO-001..004`, `RESULT-001..002`:
  `PRESERVED`.
- `ACCESS-001..004`: `REMOVED_AUTHORIZED` remains preserved.
- `ADO-001`, `WRITE-001..003`, `GOV-001`: `PRESERVED`.

## Coordinator QA focus

1. Confirm one inline editor per source row when several unresolved fields are
   present.
2. Walk the full ERP cascade and verify duplicate names stay distinguishable by
   branch.
3. Confirm a single remaining code is not applied before explicit confirmation.
4. Apply ERP correction and verify all twelve months update while another issue
   on the row remains visible.
5. Recheck organization hierarchy, scenario, `Весь год`, preview and export.

`READY_FOR_COORDINATOR_QA`
