# HANDOFF — Owner UX Smoke: persistent ERP catalogs

HANDOFF-ID: `HANDOFF-OWNER-UX-SMOKE-REFERENCE-CATALOGS-20260813-001`  
DATE: `2026-08-13`  
REPOSITORY: `fitera2024-rgb/excel-transform-1c`  
PR: `#4`  
BRANCH: `feat/v1-excel-transform-preview`  
FIX CODE HEAD: `7bc1e1bed0e9ea4d7641a5721e174ffe9f24c9ee`  
STATUS: `FIXED / CI_PASSED / OWNER_UX_SMOKE_RETRY_REQUIRED / NO_MERGE`  
SAFETY: `NO ADO / NO LIVE WRITE`

## Owner observation

The local application started successfully and the UI was visible.

Loading a real ERP reference failed with:

`Не найден заголовок известной ERP-выгрузки`

The browser URL and application error confirmed that the first adapter required the name and code headers to be on one exact row, while the real export may place them on different rows of a multi-level header.

## Accepted owner decisions

### Global organization and node catalog

- The ERP organization hierarchy is loaded once into one local catalog.
- The catalog is not copied or partitioned per selected organization.
- It remains available for all organizations and future runs in the same local installation.
- The user selects the required organization or node from this common tree.
- A later import supplements the catalog and updates existing records by stable ERP code.
- Records absent from a supplement are not silently deleted.

### Global scenario catalog

- The full ERP scenario list is loaded once.
- It persists locally for future runs.
- Additional ERP exports may add or update scenarios.
- A user may also add a local scenario manually.
- Existing scenarios keep their stable local ID.
- A later import with an ERP code may confirm/update an existing local scenario.

## Implementation

### Structural reference detection

The adapter now:

- searches the first 120 rows of every sheet;
- detects name and code headers independently;
- accepts headers on different rows;
- supports documented wording variants for articles, organizations and scenarios;
- scores candidate column pairs using the actual data below them;
- keeps structural detection independent of filenames;
- preserves leading zeroes when an ERP code is numeric with an Excel zero format.

### Persistent supplements

Local persistence now:

- stores one global `erp_articles` catalog;
- stores one global `organizations` catalog;
- merges repeated imports by stable code;
- updates a matching code and appends a new code;
- keeps previously loaded records not present in a supplement;
- upserts scenarios by canonical name + year;
- preserves scenario local IDs.

## Independent CI evidence

GitHub Actions `V1 CI`, run `31636475885`:

- compileall: PASS;
- unit: `14 passed`;
- integration: `18 passed`;
- UI smoke: `7 passed`;
- full suite: `39 passed`;
- no tracked `.xlsx/.xls/.xlsm`: PASS.

All fixtures are synthetic structural facsimiles. No real business workbook was committed.

## Owner UX Smoke retry

The owner should use the latest PR head, restart the service, then load:

1. `СтатьиДоходовИРасходовЕРП.xlsx`;
2. `ОрганизациииерархияЕРП.xlsx`;
3. `СЦЕНАРИИ_СПР_ЕРП.xlsx`.

Expected researched counts:

- ERP articles: `271`;
- organizations/nodes: `357`;
- scenarios: `12`.

After successful imports, continue the original smoke: select organization/node, select scenario/year, process the budget workbook, inspect preview/issues, apply one correction, and export OPIU Light.

PR remains Draft. Merge is not authorized before owner acceptance.
