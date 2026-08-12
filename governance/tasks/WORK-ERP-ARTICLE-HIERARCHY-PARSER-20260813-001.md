# WORK — ERP article hierarchy parser

WORK-ID: `WORK-ERP-ARTICLE-HIERARCHY-PARSER-20260813-001`  
RISK: `L`  
STATUS: `OWNER_ACCEPTED_A_PLUS_D / READY_FOR_IMPLEMENTATION / NO_MERGE`  
ISSUE: `#8`  
REPOSITORY: `fitera2024-rgb/excel-transform-1c`  
START BASE: `e96fb403da7b96a5707ba131cb141788fe27bde3`  
WORK BRANCH: `fix/erp-article-hierarchy-parser`  
TARGET BRANCH: `feat/v1-excel-transform-preview`  
SAFETY: `NO ADO / NO LIVE WRITE`

## Read before implementation

1. `AGENTS.md`
2. `docs/PRODUCT.md`
3. `docs/USER_FLOW.md`
4. `docs/ARCHITECTURE.md`
5. `governance/DECISIONS.md`
6. `governance/FEATURE_BASELINE.md`
7. `governance/ACTIVE_WORK.md`
8. GitHub Issue `#8`
9. Draft research PR `#6`
10. `governance/research/RESEARCH-ERP-MAPPING-AY-PV-20260813-001.md` from research head `14bd2c3020043a1affd0adace81a06775bed660b`

Before changes, verify:

```text
git branch --show-current
# fix/erp-article-hierarchy-parser

git rev-parse HEAD
# task-contract head on this branch, descended from e96fb403...
```

## Accepted owner decision

Implement sequence `A + D`:

- repair ERP hierarchy parsing first;
- preserve exact full-path mapping as the only automatic assignment;
- resolve the small remainder through explicit hierarchical user selection;
- do not introduce fuzzy, typo, case-only, or name-only autofix;
- keep `Удалить` / `!!!Удалить` visible.

## Defect to close

The current parser distorts the official article or full path when:

1. the ERP-code row contains technical analytics such as an account value and this value is incorrectly pushed into the hierarchy stack;
2. Excel `indent` and `outlineLevel` encode hierarchy with different scales but are compared directly.

The research found distorted name/path for 249 of 271 ERP records. Diagnostic reconstruction produces exact mapping for 368 of 379 AY/PV budget rows.

## Required implementation

- treat the nearest preceding official hierarchy row as the article node for a following ERP code;
- do not let technical analytics on the code row replace the official article;
- derive a deterministic scale conversion between Excel indent and outline depth for the documented export structure;
- preserve 271 records and stable unique ERP codes;
- preserve hierarchy branches marked `Удалить` / `!!!Удалить`;
- keep structural detection independent of filename;
- keep exact, case-sensitive full path as the mapper authority;
- fail visibly on an unsupported or ambiguous hierarchy structure rather than guessing.

## File ownership

Primary:

- `src/excel_transform_1c/adapters/references.py`
- parser-only helpers
- parser/reference unit and integration tests
- one parser implementation handoff

Forbidden without `CROSS_STREAM_DEPENDENCY` comment in Issue `#8`:

- normal UI templates;
- protected/streaming upload flow;
- inline attention editor;
- ADO or write paths.

## Required tests

Use synthetic fixtures only. Cover:

- official article on the row preceding the code;
- non-empty technical analytics on the code row;
- two indent units representing one business hierarchy level;
- outline-level hierarchy;
- adjacent sibling groups remaining siblings;
- preserved delete-marked branches;
- duplicate full paths staying visible/ambiguous;
- structurally equivalent examples for research codes `ЦБ-000239` and `00-000150` without copying real workbook data;
- full regression suite.

## Deliverables

- code and tests in this branch;
- Draft PR targeting `feat/v1-excel-transform-preview`;
- handoff `governance/handoffs/HANDOFF-ERP-ARTICLE-HIERARCHY-PARSER-20260813-001.md`;
- exact base/head, changed files, test commands/results and CI;
- final Issue/PR marker `READY_FOR_COORDINATOR_QA`.

Do not merge.