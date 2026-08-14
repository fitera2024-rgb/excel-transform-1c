# Handoff — baseline catalogs and stable identities

## Git authority

- Repository: `fitera2024-rgb/excel-transform-1c`
- Base: `feat/baselines-intalev-opiu-repair@5023ebb21bd6d9138ccc19ce3c2acf5e8b50db48`
- Work branch: `work/baseline-catalogs-v1`
- Draft PR: `#21`

## Implemented

- packaged read-only baseline catalogs for ERP articles, organization nodes, scenarios and Intalev CFOs;
- exact identity validation without display-name guessing;
- initial bootstrap for a brand-new local database;
- first explicit user import replaces only the corresponding packaged baseline;
- subsequent imports merge by exact stable identity;
- pre-upgrade stores with existing catalogs remain user-owned;
- manually added scenarios supplement the current scenario catalog;
- baseline JSON files are included in the built Python wheel.

## Catalog invariants

- ERP articles: `271` unique codes;
- organization nodes: `357` unique node IDs;
- scenarios: `12` unique exact name/year keys;
- Intalev CFOs: `15` unique exact source keys.

## Verification

- compile: PASS;
- targeted and full regression: `76 passed`;
- wheel build: PASS;
- all five baseline JSON resources present in wheel: PASS;
- tracked business Excel: `0`;
- migration payload directory removed from the final implementation tree.

## Boundaries

`DRAFT / NO MERGE / NO RELEASE / NO ADO / NO ODBC / NO 1C / NO LIVE WRITE / NO REAL BUSINESS EXCEL`

`READY_FOR_COORDINATOR_QA`
