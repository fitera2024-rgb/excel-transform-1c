# Handoff — canonical PR #24 + PR #25 preview/export integration

STATUS: `READY_FOR_COORDINATOR_QA_CANONICAL_INTEGRATION / CI_GREEN / WINDOWS_PACKAGE_GREEN / DRAFT / NO_MERGE / NO_RELEASE / NO_LIVE_WRITE`

## 1. Identification

- WORK-ID: `WORK-CANONICAL-PREVIEW-EXPORT-20260817-001`.
- TASK-ID: `CODEX-TASK-CANONICAL-PREVIEW-EXPORT-INTEGRATION-20260817-001`.
- QA-ID: `COORDINATOR-QA-CANONICAL-PREVIEW-EXPORT-20260817-001`.
- Owner gate date: `2026-08-17`.
- Repository: `fitera2024-rgb/excel-transform-1c`.
- Issue: `#27`.
- Canonical Draft PR: `#28`.
- Branch: `integration/canonical-preview-export-v1`.
- Common source base: `b712cadba6d035108c56dcc9746ff42443c3b07c`.
- Exact contract head before semantic integration: `ab4513ed6923f56a8e8ee6dd36cfbf0e8ff04465`.
- Mandatory PR #25 code/package ancestor: `c713cee112e4b935b3a5b2c319d23fc6cbf180cb`.
- Mandatory PR #24 parent/head: `77645317b673b2e57dea803410126a61cdaf6d83`.
- Exact two-parent code merge: `b5bf1d4b481a996cbf7f8b1c72e939f655670f81`.
- Exact tested implementation/workflow head: `32e17c228c9414a048484dc29dbf90d2cd264ff9`.
- Governance state before this handoff: `f00044a8bd0e09d80e06b6a2c2cdb57c2e21f6bd`.

The commit that adds this handoff is governance-only. Its exact delivery SHA cannot be self-referentially stored inside the same commit; it must be recorded in Draft PR #28 and Issue #27 after the repeat exact-head workflow completes.

## 2. Owner decision implemented

The owner explicitly decided that PR #25 does not supersede PR #24. The next canonical preview/export release candidate must preserve both lines:

1. full BDR with KPI, revenue and expenses;
2. prepared budget workbooks;
3. annual and one-month Intalev OPIU;
4. exact OPIU resolution:
   `disclosure group → article inside the group → supported exact formula/source conditions → indicator`;
5. source reconciliation and package changes from PR #25;
6. three output sheets:
   `OPIU Light / ОПИУ / Показатели`;
7. no ADO, ODBC, SQL/1C write or live write.

## 3. Git lineage and publication proof

The integration was created as an ordinary two-parent commit. No squash, rebase, whole-PR cherry-pick or history rewrite was used.

Merge commit:

`b5bf1d4b481a996cbf7f8b1c72e939f655670f81`

Parents:

1. `ab4513ed6923f56a8e8ee6dd36cfbf0e8ff04465` — canonical contract branch containing PR #25 ancestry and integration contracts;
2. `77645317b673b2e57dea803410126a61cdaf6d83` — exact PR #24 head.

Required ancestry checks passed:

```text
c713cee112e4b935b3a5b2c319d23fc6cbf180cb  → ancestor of canonical head
77645317b673b2e57dea803410126a61cdaf6d83  → ancestor of canonical head
```

The controlled publication job independently verified:

- payload SHA-256;
- binary patch SHA-256;
- exact tree object;
- exact two-parent commit object;
- both ancestry assertions;
- fast-forward from the pinned canonical contract head.

Publication workflow run: `31977588077`, job `95239296097`, `SUCCESS`.

PR #24 and PR #25 remain unmerged source lines. Conflict-discovery PR #26 is superseded by Draft PR #28 and must not be merged.

## 4. Semantic conflict resolution

The ordinary merge exposed seven conflict areas. None was resolved by unexplained whole-file `ours` or `theirs` selection.

### 4.1. `governance/ACTIVE_WORK.md`

Combined the owner gate, exact Git authority, semantic integration result, tests, package evidence and independent QA/Owner Smoke gates. Historical stream-specific active states are no longer release authority.

### 4.2. `packaging/user/README_USER_RU.md`

Preserved PR #25 long-Windows-path/runtime instructions and PR #24 business description of formula/source files. Technical Rules management was not reintroduced into normal-user instructions.

### 4.3. `src/excel_transform_1c/adapters/excel.py`

Preserved full-BDR/KPI/revenue/expense parsing, exact source coordinates, saved-value handling and expanded canonical export columns. Preserved the OPIU formula/source output attributes required by the PR #24 resolver.

### 4.4. `src/excel_transform_1c/application/service.py`

Combined the two business flows with explicit precedence:

1. direct KPI and exact dedicated revenue/quantity resolvers remain authoritative for their supported rows;
2. accepted disclosure-group/formula/source rules resolve applicable OPIU expense/revenue rows;
3. a conflicting legacy classifier cannot override formula/source authority;
4. the legacy classifier remains only as exact `group + article` fallback when no formula/source authority exists;
5. unsupported or ambiguous formula/source clauses remain unresolved and visible;
6. no global article-name-only, fuzzy, contains, typo or case-only assignment is allowed.

The record now keeps `indicator_match_source`, allowing tests/support to distinguish direct, formula/source and legacy-fallback outcomes without exposing technical workflow to normal users.

### 4.5. `src/excel_transform_1c/ui/app.py`

Preserved the full-BDR upload/preview context and the PR #24 accepted formula/analytics/MXL inputs. The normal UI remains business-oriented; no universal Rules editor, proof JSON or source-proof screen was added.

### 4.6. `src/excel_transform_1c/ui/templates/run.html`

Preserved full-BDR KPI/revenue/expense diagnostics, source pointers, correction controls and PR #24 unresolved OPIU business reasons. Both are shown without technical rule internals becoming mandatory UI.

### 4.7. Indicator tests

Preserved both parent test families and added combined regressions proving:

- KPI remains a direct result and is not forced through an expense article;
- exact formula/source rules work in the combined full-BDR service;
- formula/source authority wins over a conflicting legacy classifier;
- legacy fallback works only in an exact non-conflicting context;
- unsupported formula/source clauses fail closed and are not bypassed;
- unresolved records remain visible;
- three-sheet export remains consistent.

## 5. Preserved PR #25 capabilities

The canonical head preserves:

- full BDR structural detection as one business source;
- KPI, revenue and expense components;
- exact `sheet + row + indicator + month` identity;
- saved calculated values, including separate saved-value sheets;
- organization, department, CFO/code and channel context;
- visible Excel row separated from RUN-local identity;
- individual and bulk confirmations after composite-BDR identity changes;
- annual and one-month Intalev OPIU behavior;
- canonical three-sheet export headers;
- source reconciliation semantics with no silent numeric loss;
- protected/legacy Excel intake;
- short runtime fallback for long Windows package paths;
- restart persistence and STOP behavior.

## 6. Preserved PR #24 capabilities

The canonical head preserves:

- `src/excel_transform_1c/core/opiu_rules/`;
- `src/excel_transform_1c/adapters/opiu_sources.py`;
- structural import of accepted formula, analytics and MXL sources;
- disclosure-group-first exact resolution;
- supported exact predicates;
- fail-closed unsupported clauses;
- normalized rule persistence and restart reuse;
- combined business upload inputs;
- unresolved OPIU business rows;
- exact package smoke for OPIU rules;
- no mandatory technical Rules UI.

`core/opiu_rules` remains a narrow domain resolver for accepted OPIU sources. It is not a universal Rules Engine, plugin framework or normal-user technical editor.

## 7. Product and governance synchronization

Updated on the canonical branch:

- `docs/PRODUCT.md`;
- `docs/USER_FLOW.md`;
- `docs/ARCHITECTURE.md`;
- `governance/DECISIONS.md`;
- `governance/FEATURE_BASELINE.md`;
- `governance/ACTIVE_WORK.md`.

The synchronized contract now records:

- full BDR as an accepted structural input;
- KPI, revenue and expense completeness;
- prepared budgets and annual/monthly Intalev OPIU;
- three-sheet export;
- exact formula/source precedence;
- direct KPI semantics;
- exact legacy fallback only where allowed;
- latest owner decision removing V1 delegation/effective-access UI;
- two-parent canonical ancestry;
- narrow domain-rule boundary;
- continued prohibition of ADO/live write.

## 8. Automated verification

Canonical workflow:

`.github/workflows/canonical-preview-export.yml`

Exact tested head:

`32e17c228c9414a048484dc29dbf90d2cd264ff9`

GitHub Actions run:

`31977644700` — `SUCCESS`.

Jobs:

- `verify` — `95239411466` — `SUCCESS`;
- `windows-package` — `95239625845` — `SUCCESS`.

Results:

- `python -m compileall -q src tests scripts`: PASS;
- unit: `119 passed`;
- integration: `78 passed, 6 skipped`;
- UI: `37 passed`;
- full regression: `234 passed, 6 skipped`;
- JavaScript syntax: PASS;
- diff hygiene: PASS;
- PR #24 and PR #25 ancestry assertions: PASS;
- tracked `.xls/.xlsx/.xlsm/.xlsb/.mxl`: `0`;
- wheel resources from both parent streams: PASS.

The six skips are environment/source-specific existing tests. No test was deleted, weakened or newly skipped to make the integration green. One external Starlette/httpx deprecation warning remains and does not change business behavior.

## 9. Windows offline package

Exact package source head:

`32e17c228c9414a048484dc29dbf90d2cd264ff9`

Verified in the Windows x64 workflow:

- application wheel and complete offline wheelhouse: PASS;
- long package path and short `%LOCALAPPDATA%` runtime fallback: PASS;
- first launcher start: PASS;
- `/health` and home business markers: PASS;
- packaged module imports, including OPIU resolver: PASS;
- initial HTTP owner-flow smoke: PASS;
- synthetic full upload → preview → exact classifier → three-sheet export: PASS;
- OPIU formula/source package smoke: PASS;
- restart replaces the previous PID and preserves state: PASS;
- post-restart HTTP smoke: PASS;
- `STOP_SERVICE` and service shutdown: PASS;
- ZIP integrity: PASS.

OPIU package smoke result:

```text
OPIU_RULE_PACKAGE_SMOKE_PASS safe=2 active=4 unresolved=1
```

Package:

- artifact: `EXCEL_TO_OPIU_LIGHT_CANONICAL_PREVIEW_EXPORT_WINDOWS`;
- artifact ID: `9271686445`;
- artifact digest: `sha256:2d7f841cbb23e17418867412cedfc894e93f7863e85cff983f1aa4cbbc4a6895`;
- inner ZIP: `EXCEL_TO_OPIU_LIGHT_USER_32e17c228c94.zip`;
- inner ZIP SHA-256: `6593f1269098bdb01e294b29415ed8de66f569b85030254512075585be517931`;
- retention through `2026-08-31`.

## 10. Source reconciliation evidence

The accepted real-owner АЮ evidence from PR #25 remains the row-level reconciliation authority. It is preserved by the canonical models, source identity, export and regression tests:

- source numeric facts: `4 104`;
- output numeric facts: `4 104`;
- exact matches: `4 104`;
- Missing Output: `0`;
- Extra Output: `0`;
- Value Mismatch: `0`;
- Context Mismatch: `0`;
- formula text values in numeric output: `0`;
- source Excel errors: `12`;
- Attention: `244` unique source rows / `2 928` period rows;
- unresolved source/reference gaps: `243`;
- service defects remaining in that reconciliation: `0`.

The current GitHub canonical workflow intentionally uses synthetic package inputs. Real owner workbooks and MXL remain immutable external evidence and were not uploaded to Git or GitHub artifacts.

Equivalent full reconciliation for ПВ and ПС remains an Owner UX Smoke evidence gate when those files are available outside Git. It must distinguish source Excel errors/reference gaps from service defects and must not introduce guessed mappings.

## 11. Feature Baseline result

Result: `PASS / PRESERVED + OWNER_AUTHORIZED_EXTENSIONS`.

Preserved:

- structural detection, not filename heuristics;
- exact immutable RUN-local input handling;
- maximum-completeness preview;
- visible attention and source pointers;
- exact ERP/CFO/indicator behavior;
- 12-month normalization;
- three-sheet row-level/aggregate export;
- no silent data loss;
- no fuzzy/name-only guessing;
- no live write.

Authorized extensions recorded:

- full BDR input;
- KPI/revenue/expense components;
- exact disclosure-group/formula/source indicator resolution;
- direct KPI precedence;
- exact legacy fallback boundary;
- canonical two-parent lineage.

No accepted capability from either parent was intentionally removed.

## 12. Independent coordinator QA gate

Independent QA must now verify on the exact delivery head:

1. Draft PR #28 remains open, Draft and unmerged;
2. both mandatory source heads remain ancestors;
3. the final handoff commit changes only governance unless otherwise declared;
4. repeat exact-head workflow is green;
5. package artifact belongs to the same exact head;
6. no ADO/ODBC/SQL/1C/live-write path exists;
7. no real owner Excel/MXL/password/runtime database is tracked;
8. conflict decisions match the actual diff;
9. Product, User Flow, Architecture, Decisions, Feature Baseline and Active Work agree;
10. Owner UX Smoke instructions are business-readable.

Allowed QA result:

- `CHANGES_REQUIRED_CANONICAL_INTEGRATION`; or
- `READY_FOR_OWNER_UX_SMOKE_CANONICAL_PREVIEW_EXPORT`.

QA does not merge or release.

## 13. Owner UX Smoke

Use one exact package produced by the final delivery-head workflow.

1. Start the service with `START_SERVICE.cmd`.
2. Load a real full BDR workbook.
3. Inspect KPI, revenue and expense preview; verify organization, department, CFO/code, channel, period, value and source row/cell.
4. Verify one automatically resolved OPIU indicator and one unresolved/attention case. The unresolved case must remain visible without guessing.
5. Perform one individual supported correction and one supported bulk confirmation; verify related months update without a full rerun and unrelated reasons remain.
6. Export and inspect all three sheets: `OPIU Light`, `ОПИУ`, `Показатели`.
7. Restart the service and verify persisted catalogs/mappings/rules and repeated export.
8. Stop the service with `STOP_SERVICE.cmd` and verify it no longer responds.

Where external immutable files are available, record equivalent ПВ/ПС source reconciliation before release acceptance.

## 14. Remaining gates

- repeat exact-head CI after this governance-only handoff commit;
- independent coordinator QA;
- Owner UX Smoke on one exact delivery package;
- explicit owner acceptance;
- separate merge decision.

No merge or release is authorized by this handoff.

## 15. Safety

- `NO MERGE`.
- `NO RELEASE`.
- `NO ADO`.
- `NO ODBC`.
- `NO DIRECT SQL WRITE`.
- `NO 1C WRITE`.
- `NO LIVE WRITE`.
- `NO FUZZY / CONTAINS / TYPO / CASE-ONLY MATCHING`.
- `NO REAL OWNER EXCEL/MXL/PASSWORD/RUNTIME DB IN GIT`.

Final marker:

`READY_FOR_COORDINATOR_QA_CANONICAL_INTEGRATION`
