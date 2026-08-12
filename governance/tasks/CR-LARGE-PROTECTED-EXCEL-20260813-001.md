# CR — Large and protected budget Excel intake

CR-ID: `CR-LARGE-PROTECTED-EXCEL-20260813-001`  
RISK: `M`  
STATUS: `OWNER_REQUESTED / READY_FOR_IMPLEMENTATION / NO_MERGE`  
ISSUE: `#7`  
REPOSITORY: `fitera2024-rgb/excel-transform-1c`  
START BASE: `e96fb403da7b96a5707ba131cb141788fe27bde3`  
WORK BRANCH: `perf/streaming-protected-excel`  
TARGET BRANCH: `feat/v1-excel-transform-preview`  
SAFETY: `NO ADO / NO LIVE WRITE`

## Read before implementation

1. `AGENTS.md`
2. `docs/PRODUCT.md`
3. `docs/USER_FLOW.md`
4. `docs/ARCHITECTURE.md`
5. `governance/DECISIONS.md`
6. `governance/FEATURE_BASELINE.md`
7. `governance/ACTIVE_WORK.md`
8. GitHub Issue `#7`

Before changes, verify:

```text
git branch --show-current
# perf/streaming-protected-excel

git rev-parse HEAD
# task-contract head on this branch, descended from e96fb403...
```

## Business problem

Real protected budget workbooks are multi-megabyte files with formulas, formatting and service objects. Current synchronous full-body upload and repeated non-read-only workbook opens appear frozen and may fail before the application handler. The user needs a responsive local flow and a clear processing state.

## Required implementation

1. Stream `UploadFile` to the RUN-local input area in chunks; do not call one unbounded `await UploadFile.read()` for budget workbooks.
2. Preserve the exact original upload as the immutable source snapshot.
3. Detect protected OOXML/OLE input structurally.
4. Accept an optional workbook password.
5. Decrypt to a separate local working copy using a narrow Python adapter/library; Microsoft Excel COM must not be required at runtime.
6. Keep the password in memory only for the request. Never persist it to SQLite, run metadata, logs, filenames, Git, handoff or UI after submission.
7. Wrong or missing password returns a clear Russian business message and a reselect/retry action; the server remains available.
8. Move CPU/blocking Excel work outside the main async event loop.
9. Use `openpyxl` with `read_only=True`, `data_only=True` for budget detection/reading where compatible.
10. Close every workbook deterministically.
11. Detection scans only the structural header area; transformation reads only the selected candidate range and required columns.
12. Avoid unnecessary repeated workbook opens; document any unavoidable reopen and its reason.
13. Show `Файл загружается и анализируется; не закрывайте страницу` and prevent duplicate submit.
14. Add a lightweight responsiveness proof such as `/health` if needed.

## File ownership

Primary:

- `src/excel_transform_1c/adapters/excel.py`
- a new narrow protected-OOXML adapter if needed
- upload-specific application workflow
- minimal processing-state UI needed for this stream
- upload/protected/large-file tests
- one upload implementation handoff

Forbidden without `CROSS_STREAM_DEPENDENCY` comment in Issue `#7`:

- ERP hierarchy parser semantics;
- exact mapping rules;
- inline attention/ERP-tree editor;
- ADO or write paths.

## Required tests

Synthetic data only:

- chunked file-like upload without loading the complete payload into application bytes;
- large synthetic workbook upload → detection → preview;
- correct protected OOXML password;
- wrong password;
- missing password for protected file;
- plain `.xlsx` remains supported;
- workbook close on success and failure;
- duplicate submit is blocked in UI;
- visible processing-state text;
- GET/health responds while analysis runs;
- exact original and decrypted working copy are separate;
- password does not appear in persistence or logs;
- full regression suite.

## Deliverables

- code and tests in this branch;
- Draft PR targeting `feat/v1-excel-transform-preview`;
- handoff `governance/handoffs/HANDOFF-LARGE-PROTECTED-EXCEL-20260813-001.md`;
- exact base/head, changed files, dependency choice, test results and CI;
- final Issue/PR marker `READY_FOR_COORDINATOR_QA`.

Do not merge.