# Handoff — Owner Gate: canonical preview/export release

STATUS: `OWNER_ACCEPTED / L_INTEGRATION_AUTHORIZED / NO_MERGE / NO_RELEASE / NO_LIVE_WRITE`

## Identification

- Date: `2026-08-17`.
- Repository: `fitera2024-rgb/excel-transform-1c`.
- Issue: `#27`.
- Canonical integration branch: `integration/canonical-preview-export-v1`.
- Initial exact parent from PR #25: `c713cee112e4b935b3a5b2c319d23fc6cbf180cb`.
- Mandatory exact parent from PR #24: `77645317b673b2e57dea803410126a61cdaf6d83`.
- Common product base: `b712cadba6d035108c56dcc9746ff42443c3b07c`.
- Conflict-discovery PR: `#26`.

## Explicit owner decision

The next canonical preview/export release includes both accepted development lines.

It must contain simultaneously:

1. full BDR processing with KPI, revenue and expenses;
2. prepared budget workbooks;
3. annual and one-month Intalev OPIU;
4. exact OPIU formula/source semantics from PR #24:
   `disclosure group → article inside the group → supported exact formula/source conditions → indicator`;
5. full-BDR, source-reconciliation and package changes from PR #25;
6. the three output sheets `OPIU Light`, `ОПИУ`, `Показатели`;
7. no ADO, ODBC, direct SQL, 1C write or live write.

PR #25 does not supersede PR #24. Neither source PR is the canonical release by itself.

## Required Git result

The integration must produce one ordinary two-parent merge lineage preserving both exact heads. Squash, rebase and history rewrite are forbidden.

The final integration commit must prove:

- PR #25 head is an ancestor;
- PR #24 head is an ancestor;
- overlapping business files were resolved semantically rather than by whole-file `ours`/`theirs` selection.

## Product boundary

`core/opiu_rules` is accepted only as a narrow domain resolver for the proven OPIU inputs and exact conditions. It must not become:

- a universal Rules Engine;
- a plugin framework;
- a normal-user technical rules editor;
- a source-proof or evidence-JSON workflow.

## Mandatory gates after implementation

1. independent coordinator review of exact parents, diff, tests, CI and handoff;
2. source reconciliation for the supported owner books where evidence is available;
3. offline Windows package smoke on the exact final head;
4. Owner UX Smoke on one exact package;
5. explicit merge decision after the smoke.

## Safety

`NO MERGE / NO RELEASE / NO ADO / NO ODBC / NO SQL WRITE / NO 1C WRITE / NO LIVE WRITE`
