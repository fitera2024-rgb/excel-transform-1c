# Handoff — OPIU ERP Formula Rule Builder and Integration QA

STATUS: `READY_FOR_OWNER_UX_SMOKE / DRAFT / NO_MERGE / NO_LIVE_WRITE`

## Git authority

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Latest accepted product parent: `b712cadba6d035108c56dcc9746ff42443c3b07c`.
- Recovered CODEX-03 parent: `63d2e35244ae3fccc82bdef4fd1d702979219ad0`.
- Exact two-parent integration commit: `8bf4aa54b19d53d4e93aa48d6c8addcf82561697`.
- Unresolved-row regression fix: `2d8b750a0b2c798d67f6e5cee1ae9bcdbeafa16f`.
- Exact tested package head: `8175c02a1cefaff3f4e2dd3e1377ff2a72ff41e6`.
- Integration branch: `integration/opiu-erp-rules-v1`.
- No rebase, squash, force push or merge into the product branch was performed.
- Safety boundary: `NO ADO / NO ODBC / NO 1C WRITE / NO LIVE WRITE`.

## Owner business contract

The report indicator is determined by the exact disclosure hierarchy:

`disclosure group → article inside that group → supported exact formula/source conditions → report indicator`.

An article name alone is never authority. The same article under different disclosure groups may resolve to different report indicators. Fuzzy matching, contains matching, case correction, typo correction and first-candidate selection are absent.

## Source authorities processed outside Git

- `ОПИУ ФОРМУЛЫ.xlsx`: `463` formula rows;
- `ОПИУ аНАЛИТИКИ.xlsx`: `517` analytic rows;
- `ПоказателиОтчетов_ОПИУ_ЕРП.xlsx`: `682` ERP indicator entries;
- `Источники для ОПИУ_ ЕРП.mxl`: `311` source rows;
- `Регионы.xlsx`: `22` rows;
- `СЕТИ.xlsx`: `233` rows.

The source workbooks, MXL, converted copies, passwords, row-level financial data and runtime databases are not tracked by Git.

## Implemented behavior

- Added Business Core `core/opiu_rules/` with immutable DTOs, formula/MXL parsing, deterministic rule builder and exact resolver.
- Only the proven article dimension `С1/КС1` may create a disclosure group or exact article selection.
- Filters from other dimensions are not promoted to disclosure groups. Unsupported clauses remain unresolved and cannot silently influence an automatic result.
- The resolver checks the deepest exact disclosure level, the exact article inside that level, exact article code when available, and supported predicates.
- A conflicting exact article code is not ignored.
- Group-scope rules expand only through the exact current ERP article hierarchy and retain the ERP code.
- Formula-derived expense indicators may legitimately export an empty sales channel. The compatibility manual classifier still requires an explicit channel.
- Normalized formula-derived rules persist in `runtime/local.db` and survive service restart.
- The home page contains one business form for the six ERP source files. The originals are not persisted as a shared “latest file”.
- Existing direct classifier upload remains as a compatibility path.
- The export remains exactly three sheets in this order: `OPIU Light`, `ОПИУ`, `Показатели`.
- OPIU `NOT_FOUND` and `AMBIGUOUS` rows are visible in the business unresolved list rather than disappearing from the UI.

## Safe rule catalog from the real authorities

After fail-closed hardening:

- persisted safe rules: `21`;
- active exact rules after ERP hierarchy expansion: `250`;
- unresolved registry: `38`:
  - `21` ambiguous ERP indicator catalog links;
  - `9` proven disclosure groups without an explicit leaf list;
  - `5` formulas without a proven exact article/group selection;
  - `3` source conditions containing unsupported clauses.

The earlier research count of `38` candidate rules was reduced because values from `С2/С3` had been incorrectly eligible to look like disclosure groups. The hardened catalog leaves those conditions unresolved instead of guessing.

## Real owner-file smoke on the integrated implementation

### Protected AY budget

- candidate: prepared budget, rows `7–201`;
- source rows: `195`;
- monthly records: `2340`;
- indicator resolution: `189 automatic / 6 attention`;
- `Показатели`: `60` aggregated data rows;
- the six attention rows are exact ERP/article mismatches or source typos; no automatic correction was performed.

### Protected PV budget

- candidate: prepared budget, rows `7–191`;
- source rows: `184`;
- monthly records: `2208`;
- indicator resolution: `179 automatic / 5 attention`;
- `Показатели`: `60` aggregated data rows;
- three rows lack exact ERP/article identity; two rows are ambiguous because the same displayed article exists under distinct ERP codes.

### Annual Intalev OPIU

- candidate: `TDSheet`, rows `7–663`;
- source rows: `475`;
- monthly records: `5700`;
- the input remains readable and exports all three sheets;
- the source hierarchy does not expose the authoritative ERP disclosure groups required by these rules, so indicator rows remain `Требует внимания` rather than being guessed.

All original owner files remained read-only and unchanged.

## Automated verification

GitHub Actions workflow run `31875462020` completed successfully on exact head `8175c02a1cefaff3f4e2dd3e1377ff2a72ff41e6`.

Ubuntu verification:

- `python -m compileall -q src tests scripts`: PASS;
- full regression: `155 passed, 5 skipped, 1 warning`;
- JavaScript syntax: PASS;
- Git diff hygiene: PASS;
- tracked business Excel/MXL files: `0`;
- wheel contains OPIU source adapter, formula parser, resolver, builder, models, baselines and FITERA assets.

Windows offline-package verification:

- application wheel and complete x64 offline wheelhouse: PASS;
- actual `START_SERVICE`: PASS;
- health and FITERA home markers: PASS;
- HTTP owner-flow initial phase: PASS;
- packaged formula-rule transform/export smoke: PASS;
- exact three-sheet export: PASS;
- formula rule persistence after restart: PASS;
- second start replaced the previous PID: PASS;
- HTTP post-restart phase: PASS;
- `STOP_SERVICE` released the port: PASS;
- ZIP integrity and checksum: PASS.

Package evidence:

- artifact: `EXCEL_TO_OPIU_LIGHT_FITERA_OPIU_RULES_WINDOWS`;
- artifact ID: `9244651127`;
- inner ZIP: `EXCEL_TO_OPIU_LIGHT_USER_8175c02a1cef.zip`;
- inner ZIP SHA-256: `9a9469ffb7cb687751e5d625e62f5a2144bdcaf2d318cb0d40ba4c5b6fc51a8a`;
- GitHub artifact digest: `sha256:805de2f84cd651609d9849b4c60e1f947fcdc8c7367408d80e4c2962d6ba896c`;
- retention through `2026-08-29`.

The downloaded artifact was independently checked: outer archive, inner ZIP, required launcher files, offline `olefile`/`xlrd` wheels and OPIU rule modules all passed integrity checks.

## Feature baseline

- `PRESERVED`: structural Excel intake, immutable RUN-local input, two-stage CFO mapping, ERP/tax confirmations, restart persistence, three-sheet export, continue-with-attention, no live write.
- `CHANGED_AUTHORIZED`: report indicator selection now requires disclosure group before article and may use supported formula predicates and source analytics.
- `REMOVED_AUTHORIZED`: name-only and ERP-code-only fallback from the active formula-rule resolver.
- `BLOCKED_REGRESSION`: none after the unresolved-row hotfix.

## Gate

`READY_FOR_OWNER_UX_SMOKE / DRAFT / NO MERGE / NO RELEASE / NO ADO / NO ODBC / NO 1C WRITE / NO LIVE WRITE`.
