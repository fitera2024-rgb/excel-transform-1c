# Handoff — Large and protected budget Excel intake

STATUS: `READY_FOR_REPEAT_COORDINATOR_QA`
CR: `CR-LARGE-PROTECTED-EXCEL-20260813-001`
ISSUE: `#7`
BRANCH: `perf/streaming-protected-excel`
TARGET: `feat/v1-excel-transform-preview`
START BASE: `e96fb403da7b96a5707ba131cb141788fe27bde3`
TASK-CONTRACT HEAD: `cdde336e9629fe49108a9819d54e4c2679525289`
INITIAL IMPLEMENTATION HEAD: `40d967eed4fe82c2222d84deb024f35f2080a2ca`
COORDINATOR FIX / TESTED CODE HEAD: `0613b4792633088f6427d95ab37e7826c207799e`

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
- Coordinator QA fix: the large-file regression now generates a valid `4.46 MiB` synthetic XLSX with only two business rows plus a separate inert sheet containing 200,000 unique synthetic values. The production default `UPLOAD_CHUNK_SIZE = 1 MiB` is used; the test rejects `read(-1)`, requires at least five bounded 1 MiB reads, and completes detection and a 24-record preview.
- Coordinator QA fix: every unknown decrypt-stage dependency exception is converted to a neutral `ProtectedWorkbookError`; the original exception is retained only as `__cause__`. A HTTP regression injects an exception containing a synthetic credential and proves that value is absent from the response, response metadata, application metadata, runtime filenames/content and captured logs.
- Independent follow-up audit found and closed the same normalization requirement for dependency cleanup (`file.close()`) failures. Cleanup errors cannot replace an already sanitized active exception, and a new adapter plus HTTP regression covers this path without exposing the synthetic credential.
- `/health` responsiveness is verified while the real multi-MiB workbook is inside the worker-thread detection stage.

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
- Integration: `29 passed`.
- UI smoke: `16 passed` (one existing Starlette/TestClient deprecation warning).
- Full regression: `59 passed`.
- Added coverage: bounded async reads; large synthetic workbook through preview; plain and protected OOXML; correct, wrong and missing synthetic credentials; separate exact-original/decrypted snapshots; no credential persistence/logging; workbook close on success/failure; duplicate-submit state; `/health` responsiveness during worker analysis.
- Local in-app browser QA: password input and transient-use hint render; desktop form has no horizontal overflow; processing state is initially hidden and controlled by the guarded submit handler.

## CI

GitHub Actions `V1 CI` run `31653377431`, run number `45`, completed `success` for coordinator-fix code head `0613b4792633088f6427d95ab37e7826c207799e`. The coordinator added stacked-PR coverage for target `feat/v1-excel-transform-preview`; this branch did not change the workflow.

## Risks and limits

- Protected intake is limited to password-encrypted OOXML supported by `msoffcrypto-tool`; legacy binary `.xls` and unsupported encryption schemes remain out of scope.
- Formula values still depend on values cached by Excel; the service remains intentionally not an Excel Calculation Engine.
- Initial upload is staged before a candidate exists so reset/no-range does not create a RUN. Only processing a selected candidate creates the immutable RUN-local snapshot.

## Feature Baseline result

- `INPUT-001..005`, `RUN-001..003`, `UX-001..005`, `TRANS-001..003`: `PRESERVED` with intake/performance coverage strengthened by this authorized CR.
- `MAP-001..005`, `PREVIEW-001..003`, `RESULT-001..002`, `ADO-001`, `WRITE-001..003`: `PRESERVED`.
- All unrelated baseline IDs: `PRESERVED`.

Final marker: `READY_FOR_REPEAT_COORDINATOR_QA`.
