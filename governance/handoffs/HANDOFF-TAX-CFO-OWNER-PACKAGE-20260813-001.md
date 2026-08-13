# Handoff — Tax not important and Intalev CFO mapping

- Base: `6f0631edcba732005a407e2147c5970890e96a26`
- Branch: `feat/tax-cfo-owner-package`
- Status: `READY_FOR_OWNER_UX_SMOKE`
- Safety: `NO ADO / NO LIVE WRITE / NO MERGE`

Implemented:

- individual and bulk `Налогообложение неважно`;
- source-row counting and all-month update without full rerun;
- local Intalev CFO catalog;
- exact Intalev CFO to 1C node mapping;
- individual and bulk CFO confirmation;
- exclusion of already confirmed values from repeated counters;
- preservation of unrelated attention reasons;
- existing ERP bulk confirmation, protected intake, port cleanup and export retained.

Verification performed in GitHub Actions:

- unit: 21 passed;
- integration: 28 passed;
- UI: 25 passed;
- full regression: 74 passed;
- JavaScript syntax: PASS;
- tracked business Excel: 0.
