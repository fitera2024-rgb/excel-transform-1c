# Active Work

STATUS: `INTEGRATED / REAL_OWNER_FILES_PASSED / WINDOWS_PACKAGE_CI_REQUIRED / DRAFT / NO_LIVE_WRITE`

## Current vertical slice

`Built-in references → content-based Excel preparation → prepared budget or Intalev OPIU → exact ERP/tax/CFO decisions → 12-month preview → OPIU Light export`

## Canonical implementation

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Base integration: `integration/baselines-intalev-opiu-v1@41e8b9b6847a1cc55d58e7e027dec771117b0cde`.
- Draft PR: `#22`, not merged.
- Final owner-smoke branch/head will add FITERA UI, additive baseline semantics, real-file repairs, packaging and final evidence.

## Implemented

- packaged baseline catalogs: ERP articles, organizations/nodes, scenarios and Intalev CFO;
- `Загрузить / дополнить` preserves baseline and merges by exact stable identity;
- content-based OOXML/encrypted OOXML/BIFF/XML detection;
- immutable original snapshot and separate repair/conversion working copy;
- native annual Intalev OPIU detection, preview and export;
- protected AY/PV handling without Excel COM;
- exact ERP mapping, tax-not-required and CFO confirmations, including bulk actions and restart persistence;
- FITERA visual shell;
- no ADO/ODBC/1C/live write.

## Final gate before package delivery

- compile, full regression and JavaScript syntax;
- real CFO, Intalev OPIU and protected AY/PV owner-smoke;
- HTTP multipart smoke for full-size originals;
- wheel/package-content checks;
- Windows offline package build;
- actual launcher start/restart/port cleanup/STOP_SERVICE smoke;
- package artifact download and integrity check.

## Forbidden

- merge without owner acceptance;
- ADO/ODBC/1C/live write;
- fuzzy ERP or CFO assignment;
- real Excel, passwords or runtime databases in Git;
- mixing organization-of-run selection with source CFO mapping.
