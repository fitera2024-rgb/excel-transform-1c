# Handoff — OPIU ERP Formula Rule Builder and Integration QA

STATUS: `COORDINATOR_INTEGRATION_READY / REAL_OWNER_FILES_PASSED_WITH_ATTENTION / CI_PENDING / DRAFT / NO_MERGE / NO_LIVE_WRITE`

## Git authority

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Latest product parent: `b712cadba6d035108c56dcc9746ff42443c3b07c`.
- Recovered CODEX-03 parent: `63d2e35244ae3fccc82bdef4fd1d702979219ad0`.
- Planned integration branch: `integration/opiu-erp-rules-v1`.
- The integration commit must preserve both parents; no rebase, squash, force push or merge into the product branch is allowed.
- Safety boundary: `NO ADO / NO ODBC / NO 1C WRITE / NO LIVE WRITE`.

## Owner business contract

The report indicator is determined by the exact disclosure hierarchy:

`disclosure group → article inside that group → exact formula/source conditions → report indicator`.

An article name alone is never authority. The same article in different disclosure groups may resolve to different indicators. Fuzzy matching, contains matching, case correction, typo correction and first-candidate selection are absent.

## Source authorities processed outside Git

- `ОПИУ ФОРМУЛЫ.xlsx`: 463 formula rows;
- `ОПИУ аНАЛИТИКИ.xlsx`: 517 analytic rows;
- `ПоказателиОтчетов_ОПИУ_ЕРП.xlsx`: 682 ERP indicator entries;
- `Источники для ОПИУ_ ЕРП.mxl`: 311 source rows;
- `Регионы.xlsx`: 22 rows;
- `СЕТИ.xlsx`: 233 rows.

The source workbooks, MXL, converted copies, passwords, row-level financial data and runtime databases are not tracked by Git.

## Implemented behavior

- Added Business Core `core/opiu_rules/` with immutable rule DTOs, formula/MXL parsing, deterministic rule builder and exact resolver.
- Only the proven article dimension `С1/КС1` may create a disclosure group or exact article selection.
- Filters from other dimensions are not promoted to disclosure groups. Unsupported operators remain unresolved and cannot silently influence an automatic result.
- The resolver accepts the full business hierarchy and checks the deepest exact disclosure level first, then its exact article and exact predicates.
- An exact article code has priority over an otherwise equivalent blank-code rule; a conflicting code does not get ignored.
- Group-scope rules expand only through the exact current ERP hierarchy and retain the ERP article code.
- Formula-derived expense indicators may legitimately export an empty sales channel. The legacy manual classifier still requires an explicit channel.
- Formula-derived rules persist in `runtime/local.db` and survive restart.
- The home page has one business form for the six ERP source files. After the first successful upload, only normalized rules are persisted; the source files are not stored as a shared “latest file”.
- Existing direct classifier upload remains as a compatibility path.
- The three-sheet export remains exactly `OPIU Light`, `ОПИУ`, `Показатели`.

## Safe rule catalog from the real authorities

After fail-closed hardening:

- persisted safe rules: `21`;
- active exact rules after ERP hierarchy expansion: `250`;
- unresolved registry: `38`:
  - `21` ambiguous ERP indicator catalog links;
  - `9` proven disclosure groups without an explicit leaf list;
  - `5` formulas without a proven exact article/group selection;
  - `3` source conditions containing unsupported clauses.

The earlier research count of 38 candidate rules was reduced because values from `С2/С3` had been incorrectly eligible to look like disclosure groups. The hardened result keeps those conditions unresolved instead of guessing.

## Real owner-file smoke on the merged working tree

### Protected AY budget

- candidate: prepared budget, rows `7–201`;
- source rows: `195`;
- monthly records: `2340`;
- indicator matches: `189 automatic / 6 attention`;
- exported sheets: `OPIU Light`, `ОПИУ`, `Показатели`;
- first two sheets: `2340` data rows each;
- `Показатели`: `60` aggregated data rows;
- five generated expense indicators, each for 12 months;
- the six attention rows are exact ERP/article mismatches or source typos; no automatic correction was performed.

### Protected PV budget

- candidate: prepared budget, rows `7–191`;
- source rows: `184`;
- monthly records: `2208`;
- indicator matches: `179 automatic / 5 attention`;
- first two sheets: `2208` data rows each;
- `Показатели`: `60` aggregated data rows;
- three rows remain unmatched by exact ERP/article identity; two rows remain ambiguous because the same article name exists under two distinct ERP article codes.

### Annual Intalev OPIU

- candidate: `TDSheet`, rows `7–663`;
- source rows: `475`;
- monthly records: `5700`;
- input remains readable and exports all three sheets;
- the source hierarchy does not provide the ERP disclosure groups required by these formula rules, so indicator rows remain `Требует внимания` rather than being guessed.

All original owner files remained read-only and were not changed.

## Tests before GitHub CI

- compileall: PASS;
- JavaScript syntax: PASS;
- targeted resolver/parser/export tests: PASS;
- UI source-upload and persistence test: PASS;
- local suite available in the coordinator environment: `139 passed, 1 skipped`;
- two legacy-repair modules requiring the optional `xlwt` test dependency are delegated to clean GitHub CI, where `.[test]` installs the complete dependency set.

Added or strengthened coverage for:

- exact disclosure group at expense type, expense group or leaf level;
- deepest matching disclosure group priority;
- same article in different groups;
- article-code conflict and exact-code priority;
- `С2` not becoming a disclosure group;
- exact `С1/КС1` hierarchy/list/equality filters;
- unsupported source condition fail-closed behavior;
- blank channel allowed only for formula-derived indicator output;
- one-time six-source UI upload and restart persistence.

## Remaining gate

1. Publish the two-parent integration commit.
2. Run the complete Ubuntu regression and Windows offline package smoke.
3. Download and independently verify the ZIP and SHA-256.
4. Keep the PR Draft and unmerged.
5. Deliver the package for Owner UX Smoke.
