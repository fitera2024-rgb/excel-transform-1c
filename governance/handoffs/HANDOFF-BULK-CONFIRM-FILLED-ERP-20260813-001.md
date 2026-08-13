# Handoff — Bulk confirmation of filled ERP mappings

- Status: `READY_FOR_COORDINATOR_QA`
- CR: `CR-BULK-CONFIRM-FILLED-ERP-20260813-001`
- Issue: `#16`
- Repository: `fitera2024-rgb/excel-transform-1c`
- Work branch: `feat/bulk-confirm-filled-erp`
- Target branch: `integration/v1-approved-streams`
- Start base: `6f2f0aa1121093f51b229a7fc4e402b13166602f`
- Tested code and package head: `bf8b4a2e5b555ed45843fc57001d60835a852733`
- Safety: `NO ADO / NO LIVE WRITE / NO MERGE`

The exact final delivery head containing this handoff is recorded in the Draft PR and Issue marker after publication. Commits after the tested code head only normalize task and packaging text; implementation behavior is unchanged.

## Owner UX decision implemented

The attention page now provides one page-level action:

`Подтверждаю все заполненные ERP-сопоставления`

It is accompanied by:

- counter `Будет подтверждено: N строк`;
- action `Применить все заполненные`;
- a clear empty state when no eligible row exists.

## Business behavior

- One source Excel row counts once, independently of its twelve monthly records.
- Only a complete exact catalog selection is eligible:
  `Тип расходов → Группа расходов → Статья → ERP-код`.
- The bulk action never chooses or changes an ERP code automatically.
- Placeholder, missing, conflicting and catalog-mismatched values are excluded or rejected.
- Existing explicit empty hierarchy levels remain supported through the reversible UI encoding and exact empty business value.
- The server validates the entire submitted set before applying any row.
- Each accepted mapping updates all monthly records of the source row without a full rerun.
- Tax, department, CFO, amounts, monthly Excel errors and read-only reasons are not bulk-confirmed.
- Unrelated unresolved reasons remain visible.
- Individual row confirmation remains available.
- Repeated bulk apply is idempotent: identical overrides and manual mappings are not duplicated.
- The manual mapping key remains unchanged: report type plus full source business path.

## Implementation files

- `src/excel_transform_1c/application/service.py`
- `src/excel_transform_1c/ui/app.py`
- `src/excel_transform_1c/ui/templates/run.html`
- `src/excel_transform_1c/ui/static/run.js`
- `src/excel_transform_1c/ui/static/app.css`
- `tests/ui/test_bulk_erp_confirmation.py`

No ERP parser, protected workbook adapter, reference parser, export schema or live-write path was changed.

## Regression evidence

GitHub Actions run `31668137028` completed successfully for tested/package head `bf8b4a2e5b555ed45843fc57001d60835a852733`:

- compile source, tests and packaging scripts: PASS;
- unit: `21 passed`;
- integration: `28 passed`;
- UI: `25 passed`;
- full regression: `74 passed`;
- JavaScript syntax: PASS;
- full feature diff hygiene: PASS;
- tracked `.xlsx/.xls/.xlsm`: `0`;
- Windows user-package build: PASS.

Added bulk-specific coverage verifies:

- counter by source rows rather than monthly records;
- explicit master checkbox and unchanged individual editor;
- all twelve months updated for an eligible row;
- other unresolved fields preserved;
- no full rerun and unchanged `rerun_count`;
- repeated apply without duplicate overrides or manual mappings;
- catalog mismatch rejected without partial mutation;
- zero-eligible read-only state;
- explicit empty hierarchy level accepted when it matches the catalog exactly.

## Windows user package

Workflow artifact:

- run: `31668137028`;
- artifact: `EXCEL_TO_OPIU_LIGHT_USER_WINDOWS`;
- inner ZIP: `EXCEL_TO_OPIU_LIGHT_USER_bf8b4a2e5b55.zip`;
- inner ZIP SHA-256: `d4396447cc86203cdaae454f3836f9d35a469ebda1eeedd95b46813905b9777d`.

The package contains:

- `START_SERVICE.cmd` one-click launcher;
- Russian user guide;
- application wheel;
- Windows x64 dependency wheels for offline installation;
- local `runtime` directory and build marker.

User requirements:

- Windows 10/11 x64;
- Python 3.11 or newer available through `python.exe` or the Python launcher;
- local port `8000` free.

The first launch creates `.venv` from bundled wheels and then opens `http://127.0.0.1:8000`. Reference catalogs and scenarios are stored in the package-local `runtime` directory. No external service or Internet dependency is required for installing the bundled runtime libraries.

## Remaining gates

- Owner local UX smoke with the user package.
- Recheck original protected AY/PV workbooks through the application password field on the owner's machine.
- Integrate this Draft PR into `integration/v1-approved-streams` only after coordinator review and owner acceptance.
- Repeat affected combined QA on the new exact integrated head.

No merge was performed. No ADO, ODBC, 1C or external database write exists or was invoked.

`READY_FOR_COORDINATOR_QA`
