# Handoff — Large and protected budget Excel intake

STATUS: `READY_FOR_COORDINATOR_QA`  
CR: `CR-LARGE-PROTECTED-EXCEL-20260813-001`  
ISSUE: `#7`  
BRANCH: `perf/streaming-protected-excel`  
TARGET: `feat/v1-excel-transform-preview`  
START BASE: `e96fb403da7b96a5707ba131cb141788fe27bde3`  
TASK-CONTRACT HEAD: `cdde336e9629fe49108a9819d54e4c2679525289`  
TESTED IMPLEMENTATION HEAD: `40d967eed4fe82c2222d84deb024f35f2080a2ca`

## Changed

- Budget `UploadFile` is copied to a unique local pending area in bounded 1 MiB chunks; the HTTP path no longer performs an unbounded `await budget_file.read()`.
- The exact original is hashed incrementally and copied unchanged into the selected RUN snapshot.
- OLE-signature protected OOXML is decrypted by the narrow `msoffcrypto-tool>=6,<7` adapter into a separate working copy. Microsoft Excel COM is not used.
- The optional workbook password exists only in the current request/worker call. It is absent from pending/run models, SQLite, filenames, logs and UI values.
- Missing and wrong passwords return separate Russian retry/reselect messages without taking the service down.
- Budget detection and selected-range reading use `openpyxl` with `read_only=True`, `data_only=True` and deterministic `close()` on success and failure.
- Detection scans at most the first 100 structural rows and 100 columns per sheet. Selected-range reading iterates only the candidate rows and the required column span.
- Blocking decryption, workbook detection and transformation run outside the main async event loop. `/health` remains responsive during analysis.
- The budget and candidate forms show `Файл загружается и анализируется; не закрывайте страницу` and disable duplicate submit.

Detection deliberately closes its workbook after producing serializable candidate metadata. The selected RUN-local snapshot is reopened once after the candidate is known; this is required because explicit candidate choice may cross an HTTP request and no live workbook/file handle is retained between requests.

## Preserved

- ERP hierarchy parsing and exact mapping semantics are unchanged.
- Inline correction/editor UX and its endpoints are unchanged.
- All 12-month normalization, maximum-preview, attention/error and export behavior remains unchanged.
- No ADO, live write, TEST/PROD write or merge was performed.
- Real business workbooks and real workbook credentials are not present in Git or test fixtures.

## Synthetic test evidence

- `compileall src tests` — PASS.
- Unit: `14 passed`.
- Integration: `27 passed`.
- UI smoke: `14 passed` (one existing Starlette/TestClient deprecation warning).
- Full regression: `55 passed`.
- Added coverage: bounded async reads; large synthetic workbook through preview; plain and protected OOXML; correct, wrong and missing synthetic credentials; separate exact-original/decrypted snapshots; no credential persistence/logging; workbook close on success/failure; duplicate-submit state; `/health` responsiveness during worker analysis.
- Local in-app browser QA: password input and transient-use hint render; desktop form has no horizontal overflow; processing state is initially hidden and controlled by the guarded submit handler.

## CI

`NOT_TRIGGERED`: Draft PR `#13` correctly targets `feat/v1-excel-transform-preview`, while the existing `V1 CI` workflow accepts `pull_request` events only for `main` and push events only for `feat/v1-excel-transform-preview`. No workflow run or commit status was created for this head. The local compile/unit/integration/UI/full-regression evidence above is complete; CI workflow scope was not changed by this CR.

## Risks and limits

- Protected intake is limited to password-encrypted OOXML supported by `msoffcrypto-tool`; legacy binary `.xls` and unsupported encryption schemes remain out of scope.
- Formula values still depend on values cached by Excel; the service remains intentionally not an Excel Calculation Engine.
- Initial upload is staged before a candidate exists so reset/no-range does not create a RUN. Only processing a selected candidate creates the immutable RUN-local snapshot.

## Feature Baseline result

- `INPUT-001..005`, `RUN-001..003`, `UX-001..005`, `TRANS-001..003`: `PRESERVED` with intake/performance coverage strengthened by this authorized CR.
- `MAP-001..005`, `PREVIEW-001..003`, `RESULT-001..002`, `ADO-001`, `WRITE-001..003`: `PRESERVED`.
- All unrelated baseline IDs: `PRESERVED`.

Final marker: `READY_FOR_COORDINATOR_QA`.
