# WORK — Sequential integration of approved V1 streams

WORK-ID: `WORK-INTEGRATE-APPROVED-V1-STREAMS-20260813-001`  
RISK: `L`  
STATUS: `THREE_STREAMS_QA_PASSED / READY_FOR_INTEGRATION / NO_MERGE`  
ISSUE: `#14`  
REPOSITORY: `fitera2024-rgb/excel-transform-1c`  
START BASE: `90cf73aeefd2743a2ddb15ae63db88d121acf79f`  
WORK BRANCH: `integration/v1-approved-streams`  
TARGET: `feat/v1-excel-transform-preview`  
COMBINED QA: `#10`  
SAFETY: `NO ADO / NO LIVE WRITE`

## Read first

1. `AGENTS.md`
2. `docs/PRODUCT.md`
3. `docs/USER_FLOW.md`
4. `docs/ARCHITECTURE.md`
5. `governance/DECISIONS.md`
6. `governance/FEATURE_BASELINE.md`
7. `governance/ACTIVE_WORK.md`
8. Issue `#14`
9. Issue `#10`
10. Draft PRs `#12`, `#13`, `#11` and their latest coordinator reviews/handoffs

Before any integration, verify:

```text
git branch --show-current
# integration/v1-approved-streams

git rev-parse HEAD
# contract head produced by this file commit
```

Do not modify files until the branch and contract head match GitHub.

## Accepted exact inputs

Integrate in this mandatory order:

1. **ERP parser**
   - PR: `#12`
   - branch: `fix/erp-article-hierarchy-parser`
   - accepted head: `9f9157285fe3dd09b7dc50455f3f373e28b7beb7`
   - CI: `31651849987`

2. **Large/protected Excel intake**
   - PR: `#13`
   - branch: `perf/streaming-protected-excel`
   - accepted current head: `143c4db875fbb04d6b1ec59501191b3739315361`
   - tested code head: `b61242abacc34baee1a8946e4724cfc7fbfd5893`
   - exact-current-head CI: `31652898683`

3. **Inline attention / ERP hierarchy UX**
   - PR: `#11`
   - branch: `feat/inline-attention-erp-tree`
   - accepted head: `4e389b9b0e71bebb41dd178fa68a33bff3991c55`
   - CI: `31652392216`

No other branch or commit is an approved implementation input.

## Integration method

- preserve commit history and exact provenance;
- do not squash or rewrite accepted heads;
- integrate one stream at a time in the mandatory order;
- after each integration, record the resulting exact head and run targeted tests before continuing;
- do not merge the individual Draft PRs;
- do not push directly to `feat/v1-excel-transform-preview`;
- final delivery is one Draft integration PR from this branch to the target branch.

## Authorized mechanical overlap resolution

Only mechanical combination is allowed.

### `pyproject.toml`

Preserve both:

- runtime dependency `msoffcrypto-tool>=6,<7`;
- package data for `ui/static/*.js`.

### `tests/helpers/workbooks.py`

Preserve both:

- ERP hierarchy fixtures with accepted indent scale `0/2/4`;
- large/protected synthetic workbook helpers.

### `tests/ui/test_ui_smoke.py`

Preserve all tests from both streams:

- protected/large upload, health, password non-disclosure;
- inline attention grouping, empty hierarchy sentinel, read-only reasons.

### `src/excel_transform_1c/ui/static/app.css`

Preserve both processing-state/password layout and inline-attention/editor styles.

### Other overlaps

If an overlap requires choosing one business behavior over another, stop with:

`INTEGRATION_SEMANTIC_CONFLICT`

State the files, exact hunks and conflicting requirements. Do not guess.

## Forbidden

- new product behavior;
- fuzzy/name-only/case/typo auto-mapping;
- weakening parser fail-closed rules;
- persisting or redisplaying a workbook password;
- changing manual-mapping key semantics;
- changing organization/scenario/period owner decisions;
- adding ADO, 1C, DB or live write;
- committing real Excel files or credentials;
- merging to target or main.

## Verification after all three streams

Run and record:

```text
git diff --check
python -m compileall -q src tests
python -m pytest tests/unit -q
python -m pytest tests/integration -q
python -m pytest tests/ui -q
python -m pytest -q
node --check src/excel_transform_1c/ui/static/run.js
```

Also verify:

- no tracked `.xlsx/.xls/.xlsm`;
- no credential strings or real workbook artifacts;
- PR #4 remains Draft;
- no ADO/live write path was added;
- GitHub Actions is green on the exact combined head.

## Deliverable

1. Draft PR from `integration/v1-approved-streams` to `feat/v1-excel-transform-preview`.
2. Handoff:
   `governance/handoffs/HANDOFF-INTEGRATED-V1-STREAMS-20260813-001.md`
3. Exact provenance:
   - start head;
   - each accepted source head;
   - each sequential integration head;
   - final combined head.
4. Changed/conflict-resolved files and exact explanation of every mechanical resolution.
5. Local tests and GitHub CI.
6. Final marker in PR and Issue #14:

`READY_FOR_COMBINED_QA`

Do not merge. Independent QA begins only after the coordinator checks this delivery and records the exact combined head in Issue #10.
