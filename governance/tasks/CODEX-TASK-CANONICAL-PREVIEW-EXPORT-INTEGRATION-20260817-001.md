# CODEX TASK — Canonical Preview/Export Integration

TASK-ID: `CODEX-TASK-CANONICAL-PREVIEW-EXPORT-INTEGRATION-20260817-001`

RISK: `L`

STATUS: `READY_AFTER_EXACT_CONTRACT_HEAD_IS_PINNED / NO_MERGE / NO_RELEASE / NO_LIVE_WRITE`

## 1. Purpose

Integrate the complete accepted functionality of PR #24 and PR #25 into one canonical Draft release candidate.

This is a semantic integration task, not a new feature task. Do not expand the accepted scope.

## 2. Exact Git inputs

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Work branch: `integration/canonical-preview-export-v1`.
- Starting product/code ancestor: PR #25 exact head `c713cee112e4b935b3a5b2c319d23fc6cbf180cb`.
- Mandatory second parent: PR #24 exact head `77645317b673b2e57dea803410126a61cdaf6d83`.
- Common product base: `b712cadba6d035108c56dcc9746ff42443c3b07c`.
- Issue: `#27`.
- Conflict-discovery Draft PR: `#26`.
- Owner gate handoff: `governance/handoffs/HANDOFF-OWNER-GATE-CANONICAL-PREVIEW-EXPORT-20260817-001.md`.
- Work registry: `governance/tasks/WORK-CANONICAL-PREVIEW-EXPORT-20260817-001.md`.

Before modifying code, verify that the branch points to the exact contract head recorded in Issue #27. Stop with `START_HEAD_MISMATCH` if it does not.

## 3. Mandatory Git method

1. Work only on the existing branch `integration/canonical-preview-export-v1`.
2. Integrate `77645317b673b2e57dea803410126a61cdaf6d83` using an ordinary merge that preserves two parents.
3. Do not squash, rebase, cherry-pick the whole PR, rewrite history or force-push.
4. Do not resolve overlapping business files by wholesale `ours` or `theirs`.
5. Resolve every overlap at function/field/template/test level and record the decision in the handoff.
6. The final integration lineage must satisfy both:

```bash
git merge-base --is-ancestor c713cee112e4b935b3a5b2c319d23fc6cbf180cb HEAD
git merge-base --is-ancestor 77645317b673b2e57dea803410126a61cdaf6d83 HEAD
```

The merge/integration commit must expose both histories through its parents or ancestry.

## 4. Known overlapping files requiring semantic review

At minimum review these overlaps explicitly:

- `packaging/user/README_USER_RU.md`;
- `src/excel_transform_1c/adapters/excel.py`;
- `src/excel_transform_1c/adapters/persistence.py`;
- `src/excel_transform_1c/application/service.py`;
- `src/excel_transform_1c/core/indicator_matching.py`;
- `src/excel_transform_1c/core/models.py`;
- `src/excel_transform_1c/ui/app.py`;
- `src/excel_transform_1c/ui/templates/home.html`;
- `src/excel_transform_1c/ui/templates/run.html`;
- `tests/integration/test_article_indicator_workflow.py`;
- `tests/ui/test_ui_smoke.py`;
- `tests/unit/test_article_indicator_matching.py`.

Also inspect all 25 changed paths from PR #24 and all changed paths from PR #25. Do not assume the list above is complete after later branch movement.

## 5. Capabilities that must remain from PR #25

Preserve and verify:

- structural full-BDR detection as one business source;
- KPI, revenue and expense components;
- exact saved-value sheet resolution;
- exact source key and separation of visible Excel row from RUN-local identity;
- organization, department, CFO/code and channel context;
- annual and one-month Intalev behavior already present in PR #25;
- three-sheet export and canonical headers;
- source reconciliation semantics with no silent numeric loss;
- confirmations after composite-BDR identity changes;
- protected workbook and long-Windows-path runtime fix;
- existing owner/package smoke behavior;
- all existing PR #25 tests.

## 6. Capabilities that must remain from PR #24

Preserve and verify:

- `src/excel_transform_1c/core/opiu_rules/`;
- `src/excel_transform_1c/adapters/opiu_sources.py`;
- structural import of the accepted formula, analytics and MXL sources;
- exact resolver order:
  `disclosure group → article inside the group → supported exact source/formula predicates → indicator`;
- deepest exact disclosure-group priority where defined by the accepted implementation;
- fail-closed handling of unsupported clauses without guessing;
- persistence and restart reuse of normalized rules;
- one business upload flow for the accepted source files;
- unresolved business rows in normal UI;
- no mandatory technical Rules UI;
- package smoke that imports and exercises the OPIU resolver;
- all existing PR #24 tests.

## 7. Required combined semantics

- Full BDR processing and OPIU formula/source classification must compose; neither may bypass the other silently.
- KPI must not require an expense article.
- Expense and revenue resolver behavior may not be changed merely to satisfy OPIU rule tests.
- OPIU rule resolution may not fall back to global article-name-only matching.
- Existing direct article-indicator behavior may remain only where exact and non-conflicting with the accepted disclosure-group/source authority. Document precedence explicitly.
- Missing, unsupported or ambiguous formula/source identity remains visible as `Требует внимания`.
- `OPIU Light` and `ОПИУ` row-level outputs must remain intact while `Показатели` uses the accepted exact aggregation logic.
- Channel, organization, period, source row/cell and status information must not be lost.
- No formulas may be exported as text in the numeric value field.

## 8. Product and governance synchronization

Update the existing canonical files on the integration branch:

- `docs/PRODUCT.md`;
- `docs/USER_FLOW.md`;
- `docs/ARCHITECTURE.md`;
- `governance/DECISIONS.md`;
- `governance/FEATURE_BASELINE.md`;
- `governance/ACTIVE_WORK.md`.

Required content:

1. Full BDR is an accepted structural input containing KPI, revenue and expense components.
2. Prepared budgets and annual/monthly Intalev OPIU remain supported.
3. Three-sheet export is accepted.
4. The PR #24 exact formula/source chain is accepted.
5. PR #25 does not supersede PR #24.
6. Delegation/access wording must reflect the latest accepted owner decision already present in the implementation line; do not reintroduce removed V1 delegation UI.
7. `core/opiu_rules` is a narrow domain resolver, not a universal Rules Engine or plugin framework.
8. No ADO/live write is authorized.
9. Add stable Feature Baseline IDs for full BDR, KPI/revenue/expense completeness, formula/source resolution, three-sheet preservation and canonical integration ancestry.
10. Record the owner decision as a new DEC entry with explicit `refines/supersedes` links; do not rewrite earlier decisions silently.

## 9. Tests and verification

Run at least:

```bash
python -m compileall -q src tests scripts
python -m pytest tests/unit -q
python -m pytest tests/integration -q
python -m pytest tests/ui -q
python -m pytest -q
node --check src/excel_transform_1c/ui/static/run.js
git diff --check b712cadba6d035108c56dcc9746ff42443c3b07c...HEAD
test -z "$(git ls-files '*.xls' '*.xlsx' '*.xlsm' '*.xlsb' '*.mxl')"
```

Add focused combined regressions proving:

- OPIU rule modules and source adapter are packaged;
- full BDR KPI/revenue/expense workflow remains operational;
- exact disclosure-group/source logic works inside the combined service;
- unresolved formula/source rows remain visible;
- three sheets preserve expected row-level and aggregate behavior;
- direct article-only fallback does not override a conflicting disclosure-group authority;
- restart persistence works for both existing mappings and OPIU rules;
- protected workbook short-runtime-path behavior remains intact;
- no ADO/ODBC/1C write path exists.

Do not lower, skip or delete an existing regression merely to obtain green CI. Environment-specific skips must remain explained.

## 10. CI and package

Create or adapt one canonical workflow for the integration branch that performs:

- compile and full tests;
- JavaScript syntax and diff hygiene;
- wheel-resource verification for both parent capabilities;
- Windows x64 offline package build;
- launcher, health, HTTP upload/preview/export, restart and stop;
- OPIU formula/source smoke;
- ZIP integrity and SHA-256 artifact evidence.

Do not retain two competing release workflows as equal authorities. Older stream-specific workflows may remain as historical files only if they cannot confuse the canonical release path; otherwise document or retire them explicitly.

## 11. Deliverable

Update the existing canonical Draft PR from `integration/canonical-preview-export-v1`. Do not create a second canonical branch.

Create:

`governance/handoffs/HANDOFF-CANONICAL-PREVIEW-EXPORT-INTEGRATION-20260817-001.md`

The handoff must contain:

- exact start head;
- both mandatory parent SHAs and final ancestry proof;
- merge/conflict file list and semantic resolution for each overlap;
- changed files;
- all tests and CI run IDs;
- package artifact name, ID and digest;
- Feature Baseline result;
- source reconciliation evidence available without committing owner data;
- remaining attention/source-reference gaps separated from service defects;
- exact Owner UX Smoke steps;
- explicit safety statement.

Final marker:

`READY_FOR_COORDINATOR_QA_CANONICAL_INTEGRATION`

## 12. Forbidden

- merge to `main` or any release branch;
- closing the owner gate without coordinator QA and Owner UX Smoke;
- ADO, ODBC, direct SQL, 1C write or live write;
- fuzzy, contains, typo or case-only matching;
- global article-name-only authority;
- invented financial semantics, indicators, groups, channels or codes;
- universal Rules Engine, plugin framework or technical normal-user rules editor;
- real owner Excel/MXL, passwords, runtime DB, absolute private paths or row-level financial output in Git;
- deletion of an accepted parent capability without a new explicit owner decision.
