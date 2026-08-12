# Handoff — Inline attention correction and ERP hierarchy selector

- Status: `READY_FOR_REPEAT_COORDINATOR_QA`
- CR: `CR-INLINE-ATTENTION-ERP-TREE-20260813-001`
- Issue: `#9`
- Work branch: `feat/inline-attention-erp-tree`
- Target branch: `feat/v1-excel-transform-preview`
- Exact start head: `e54ebc6a498f42f504fe5f6cb98353b8b09e753a`
- Initial implementation head: `ee0a2a1ad3dc6aa1ce23eb903736f58893aa5d47`
- Coordinator QA fix head: `4ebbb8c7aaa1e937b7d0ca30538c788320cd15e6`
- Verified GitHub Actions run: `31652298898` — `success`
- Safety: `NO ADO / NO LIVE WRITE / NO MERGE`

The final delivery head also contains this handoff file and is recorded in the
Draft PR and Issue marker together with its green CI run. The QA fix head above
is the exact independently tested code-and-tests commit.

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

## Coordinator QA changes requested — resolved

### Empty ERP hierarchy levels

- Placeholder remains the empty HTML value and can no longer collide with a
  real empty business value.
- The UI uses `__EMPTY__` for an exact empty catalog level and a separate encoded
  prefix for every non-empty value.
- Filtering decodes each selected option back to its exact catalog value before
  comparing it, so an empty group remains `""` in business data.
- Empty type, group, article and code levels receive readable labels:
  `Корневой уровень`, `Без группы`, `Без статьи`, `Без кода`.
- Regression data covers one empty group with two articles and three codes,
  including two codes under the same article.

### Read-only attention

- Active editor is rendered only when the row contains `erp-mapping`, `tax`, or
  a supported `shared-field`: department, CFO, expense group or source article.
- `monthly-error`, `negative-amount`, `context-reporting-unit` and every other
  unsupported reason receive a read-only action next to the exact source pointer.
- A row with only unsupported reasons has no form and no apply button.
- A mixed row keeps the editor and all read-only reasons in the same visible
  attention group.

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

- Targeted UI regression: `16 passed`.
- Full local regression: `49 passed`.
- JavaScript syntax: `node --check src/excel_transform_1c/ui/static/run.js` — PASS.
- Patch hygiene: `git diff --check` — PASS.
- Console errors during browser smoke: none.
- GitHub Actions `V1 CI`, run `31652298898`: SUCCESS.
  - `Python 3.11 tests`: SUCCESS;
  - `No tracked business Excel`: SUCCESS.

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

Repeat smoke for the coordinator findings additionally confirmed:

- before selection, the empty-group placeholder has value `""` and article is
  disabled;
- real `Без группы` has UI value `__EMPTY__`;
- selecting it exposes two articles, and the selected article exposes two
  distinct ERP codes;
- a monthly-error-only row renders one attention group, zero editors, one
  read-only block and zero apply buttons;
- browser console errors/warnings: none.

## Feature Baseline result

- `PREVIEW-003`, `UX-003`, `MAP-001..005`: `CHANGED_AUTHORIZED` by Issue #9
  and the Task Contract.
- `ORG-001..004`, `PERIOD-001..002`, `SCENARIO-001..004`, `RESULT-001..002`:
  `PRESERVED`.
- `ACCESS-001..004`: `REMOVED_AUTHORIZED` remains preserved.
- `ADO-001`, `WRITE-001..003`, `GOV-001`: `PRESERVED`.

## Coordinator QA focus

1. Select `Без группы` and verify the exact empty catalog branch exposes all of
   its articles and codes.
2. Verify monthly-error and reporting-unit-conflict groups are read-only and
   contain no apply button.
3. Verify a mixed editable/read-only row keeps both the editor and every reason.
4. Recheck unique-code explicit confirmation and all-twelve-month update.
5. Recheck organization hierarchy, scenario, `Весь год`, preview and export.

`READY_FOR_REPEAT_COORDINATOR_QA`
