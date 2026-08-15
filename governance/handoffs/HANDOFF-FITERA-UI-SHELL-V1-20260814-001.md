# HANDOFF — FITERA UI SHELL V1

## Marker

`READY_FOR_INTEGRATION_UI`

## Exact base

`5023ebb21bd6d9138ccc19ce3c2acf5e8b50db48`

## Scope

Visual shell only. No application workflow, persistence, transformation or live-write semantics changed.

## Changed files

- `src/excel_transform_1c/ui/templates/base.html`
- `src/excel_transform_1c/ui/templates/home.html`
- `src/excel_transform_1c/ui/templates/run.html`
- `src/excel_transform_1c/ui/templates/blocked.html`
- `src/excel_transform_1c/ui/templates/choose_candidate.html`
- `src/excel_transform_1c/ui/static/app.css`
- `src/excel_transform_1c/ui/static/fitera-logo.png`
- `pyproject.toml` — package the PNG asset
- `tests/ui/test_fitera_shell.py`
- `governance/research/UI-SPEC-FITERA-OPIU-LIGHT-20260814-001.md`

## Preserved contracts

- all form actions and methods;
- business input names;
- `data-testid` values;
- JavaScript `data-*` hooks;
- organization hierarchy behavior;
- period behavior;
- ERP, tax and CFO confirmation flows;
- preview and export endpoints;
- no ADO / no 1C write.

## Tests

- `python -m compileall -q src tests scripts` — PASS
- `python -m pytest tests/ui -q` — `28 passed`
- `python -m pytest -q` — `77 passed`
- `node --check src/excel_transform_1c/ui/static/run.js` — PASS
- `git diff --check` — PASS

## Integration notes

If the Excel intake stream also changes `pyproject.toml`, preserve both its dependency additions and this branch's `ui/static/*.png` package-data entry.

The UI allows `.xlsx`, `.xls` and `.xlsm` selection; actual acceptance remains fail-closed in the integrated intake adapter.

## Gate

Draft only. Do not merge before combined integration tests and Owner UX Smoke.
