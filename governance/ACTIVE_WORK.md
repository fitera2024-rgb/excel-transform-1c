# Active Work

STATUS: `OWNER_REFINEMENT_IMPLEMENTED / TAX_CFO_QA_READY / PACKAGE_BUILD_REQUIRED / DRAFT / NO_LIVE_WRITE`

## Current vertical slice

`Excel → structural detection → protected intake → exact ERP mapping → tax/CFO decisions → 12-month preview → export`

## Exact base

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Parent branch: `feat/bulk-confirm-filled-erp`.
- Exact start head: `6f0631edcba732005a407e2147c5970890e96a26`.
- Parent Draft PR: `#17`, not merged.

## Owner refinement implemented

- individual and bulk `Налогообложение неважно`;
- business status `Налогообложение: не требуется`;
- structural local catalog `ЦФО Инталев`;
- exact `ЦФО Инталев → конкретный узел 1С`;
- individual and bulk CFO confirmation;
- already confirmed ERP/tax/CFO elements render as statuses and are excluded from counters;
- all updates affect source rows and their months without full rerun;
- ERP, tax and CFO remain separate explicit actions.

## Verification gate

Required before owner package delivery:

- compileall;
- unit, integration, UI and full regression;
- JavaScript syntax;
- Git diff hygiene;
- no tracked business Excel;
- Windows offline package build;
- actual launcher/restart/port cleanup/STOP_SERVICE smoke.

## Remaining owner gate

Owner UX Smoke on the new exact Windows package, including original protected AY/PV files. No ADO/live write is implemented or permitted.

## Forbidden

- merge without owner acceptance;
- ADO/ODBC/1C/live write;
- fuzzy ERP or CFO assignment;
- real Excel, passwords or runtime databases in Git;
- mixing organization-of-run selection with source CFO mapping.
