# Handoff — Integrated approved V1 streams

- Work ID: `WORK-INTEGRATE-APPROVED-V1-STREAMS-20260813-001`
- Issue: `#14`
- Repository: `fitera2024-rgb/excel-transform-1c`
- Work branch: `integration/v1-approved-streams`
- Target branch: `feat/v1-excel-transform-preview`
- Safety: `NO ADO / NO LIVE WRITE / NO MERGE`
- Combined QA: Issue `#10`

## Exact provenance

- Contract/start head: `cae26c399e92a3dda25a35b34b5f9f7bb4863b96`.
- Accepted ERP parser head: `9f9157285fe3dd09b7dc50455f3f373e28b7beb7`.
- Result after sequential integration 1: `368b9334da8ac68b0e2d19621b2bfae52f4766fa`.
- Accepted large/protected intake head: `143c4db875fbb04d6b1ec59501191b3739315361`.
- Result after sequential integration 2: `4b77b9e6e9c03b28bdb14f7a9db33ed724bac7cf`.
- Accepted inline-attention UX head: `4e389b9b0e71bebb41dd178fa68a33bff3991c55`.
- Final combined implementation head: `ba82dc2f5aecde1689b443ff428b9f8caf25fc5e`.

Each stream was integrated with a two-parent `--no-ff` merge in the mandatory
order. Accepted commits remain reachable as exact merge parents; no accepted
commit was squashed, rebased or rewritten. PRs `#12`, `#13` and `#11` remain
individual Draft PRs and were not merged on GitHub.

The documentation-only delivery commit containing this handoff is recorded as
the exact PR/Issue delivery head after publication. The combined implementation
tree under test is the exact `ba82dc2f5aecde1689b443ff428b9f8caf25fc5e`
tree stated above.

## Integrated streams

1. ERP parser:
   - preserves the nearest preceding official hierarchy node for a code row;
   - normalizes accepted ERP indent scale `0/2/4` to levels `0/1/2`;
   - fails visibly on unsupported, missing or contradictory hierarchy levels;
   - keeps exact case-sensitive full-path mapping and visible
     `Удалить` / `!!!Удалить` entries.
2. Large/protected Excel intake:
   - uses bounded 1 MiB upload reads and worker-thread analysis;
   - keeps exact original and separate decrypted working copies;
   - supports protected OOXML through `msoffcrypto-tool>=6,<7` without Excel COM;
   - does not persist or redisplay the workbook password;
   - keeps health responsive during synthetic large-workbook analysis.
3. Inline attention / ERP hierarchy UX:
   - groups attention by source row and preserves all twelve derived months;
   - provides catalog-only `type → group → article → code` selection;
   - preserves exact empty hierarchy values through a reversible UI sentinel;
   - shows unsupported reasons read-only and keeps supported corrections explicit.

No new product behavior was added by the integration itself.

## Authorized mechanical overlap resolution

Only overlaps listed in the Task Contract were combined.

### `pyproject.toml`

Git combined the streams automatically. The final file preserves both:

- runtime dependency `msoffcrypto-tool>=6,<7`;
- package data `ui/static/*.js` alongside the existing templates and CSS.

### `tests/helpers/workbooks.py`

Git combined the parser and intake streams automatically. The final file
preserves both:

- ERP hierarchy fixtures using accepted indent values `0/2/4`;
- synthetic large-workbook and protected-workbook helpers.

### `tests/ui/test_ui_smoke.py`

One textual conflict was resolved mechanically. The conflict consisted of:

- imports: preserving `asyncio`, `json`, `re` and `threading` together;
- adjacent test additions after the reporting-unit test: preserving the inline
  read-only assertions and mixed editable/read-only test, followed by the
  protected-password, health-responsiveness and credential-nondisclosure tests.

No assertion or business rule was selected over another. All `15` tests from
the intake-side file and all `16` tests from the inline-side file are present in
the `20`-test combined file; shared tests are counted once.

### `src/excel_transform_1c/ui/static/app.css`

Git combined the streams automatically. The final file preserves both:

- processing-state and workbook-password layout styles;
- inline attention, read-only reason and editor styles.

No other conflict required resolution. No semantic conflict occurred.

## Targeted verification after each integration

- After ERP parser integration at `368b9334...`:
  - parser/reference targeted suite: `10 passed`;
  - `git diff --check`: PASS.
- After large/protected intake integration at `4b77b9e6...`:
  - synthetic protected/large upload plus UI suite: `24 passed`;
  - `git diff --check`: PASS.
- After inline UX integration at `ba82dc2f...`:
  - UI suite: `20 passed`;
  - JavaScript syntax check: PASS;
  - every test function from both overlapping UI files is retained.

## Full local verification

Only synthetic fixtures were used. Owner UX Smoke, real ERP references, real
AY/PV budget workbooks, real passwords and Excel COM were not used.

- `git diff --check` — PASS.
- `python -m compileall -q src tests` — PASS.
- `python -m pytest tests/unit -q` — `21 passed`.
- `python -m pytest tests/integration -q` — `28 passed`.
- `python -m pytest tests/ui -q` — `20 passed`, one external
  Starlette/httpx deprecation warning.
- `python -m pytest -q` — `69 passed`, one external Starlette/httpx
  deprecation warning.
- `node --check src/excel_transform_1c/ui/static/run.js` — PASS.

Repository guards:

- tracked `.xlsx`, `.xls` or `.xlsm`: `0`;
- no real workbook artifact or real credential was added;
- password values in tests are explicitly synthetic fixtures only;
- parent PR `#4` remains open, Draft and unmerged;
- local SQLite persistence remains the existing V1 adapter and was not changed;
- no ADO/ODBC/1C live-write adapter or path was added;
- no merge to the target branch or `main` was performed.

## Feature Baseline result

- ERP parser changes authorized by Issue `#8`: preserved exactly.
- Large/protected intake changes authorized by Issue `#7`: preserved exactly.
- Inline attention changes authorized by Issue `#9`: preserved exactly.
- `MAP-001..005`, `INPUT-001..005`, `RUN-001..003`, `TRANS-001..003`,
  `PREVIEW-001..003`, `ORG-001..004`, `SCENARIO-001..004`,
  `PERIOD-001..002`, `RESULT-001..002`, `ADO-001`, `WRITE-001..003` and
  `GOV-001`: `PRESERVED`.
- No unrelated baseline behavior was changed by mechanical integration.

## Remaining gate

Publish this branch, open one Draft PR to `feat/v1-excel-transform-preview`,
and require green GitHub Actions on the exact delivery head. Independent
combined QA begins under Issue `#10` only after that exact head is recorded.

`READY_FOR_COMBINED_QA`
