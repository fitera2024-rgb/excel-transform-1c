# CR — Inline attention correction and ERP hierarchy selector

CR-ID: `CR-INLINE-ATTENTION-ERP-TREE-20260813-001`  
RISK: `M`  
STATUS: `OWNER_REQUESTED / READY_FOR_IMPLEMENTATION / NO_MERGE`  
ISSUE: `#9`  
REPOSITORY: `fitera2024-rgb/excel-transform-1c`  
START BASE: `e96fb403da7b96a5707ba131cb141788fe27bde3`  
WORK BRANCH: `feat/inline-attention-erp-tree`  
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
8. GitHub Issue `#9`
9. Research findings in Draft PR `#6`, especially the recommended sequence `A + D`

Before changes, verify:

```text
git branch --show-current
# feat/inline-attention-erp-tree

git rev-parse HEAD
# task-contract head on this branch, descended from e96fb403...
```

## Accepted UX change

The current separate correction form requires an opaque source-row selector and is not understandable to a normal user. Correction must be embedded in the relevant `Требует внимания` context.

ERP codes must be selected through business hierarchy, not one long flat list.

## Required implementation

### One editor per source row

- remove the separate top correction form;
- group unresolved issues and monthly records by source Excel row;
- render one correction editor for one source row, not twelve editors for twelve months;
- place the editor next to or immediately below the corresponding attention group;
- show source article, expense type, expense group, current ERP mapping, reason, sheet/cell and affected months;
- keep source-row number as secondary detail only;
- applying a correction updates all months derived from that source row without a full rerun;
- fixing one field must not hide other unresolved fields.

### ERP hierarchy cascade

Implement:

`Тип расходов → Группа расходов → Статья → ERP-код`

- options come only from the loaded ERP catalog;
- every level filters the next;
- the final code is shown with the complete path and official ERP name;
- duplicate names in different branches remain distinguishable;
- one remaining code may be preselected but still needs explicit confirmation;
- `Удалить` / `!!!Удалить` remain visible;
- no fuzzy, typo, case-insensitive or name-only automatic assignment;
- manual mapping remains keyed by report type + complete source path;
- catalog/manual conflicts remain visible as `Требует внимания`.

### Preserve existing UX

- hierarchical organization selection;
- all organizations visible to all local users;
- scenario selector;
- `Весь год` default;
- maximum-completeness preview;
- OPIU Light export;
- no ADO/live write.

## File ownership

Primary:

- `src/excel_transform_1c/ui/templates/run.html`
- `src/excel_transform_1c/ui/static/*`
- UI-specific view models/helpers only when necessary
- `tests/ui/*`
- one UI implementation handoff

Do not change ERP parser, protected/streaming upload adapter or financial mapping semantics. Before editing `service.py` or `app.py`, post `CROSS_STREAM_DEPENDENCY` in Issue `#9` with the exact DTO/context needed.

## Required tests

- standalone opaque source-row selector absent;
- one editor per source row;
- the editor shows reason and exact source cell;
- type filters groups;
- group filters articles;
- article filters codes;
- duplicate article names in different branches stay separate;
- unique code preselection still requires submit confirmation;
- correction updates all months of the source row;
- another unresolved issue on the same row stays visible;
- scenario, organization hierarchy and `Весь год` remain present;
- full regression suite.

## Deliverables

- code and tests in this branch;
- Draft PR targeting `feat/v1-excel-transform-preview`;
- handoff `governance/handoffs/HANDOFF-INLINE-ATTENTION-ERP-TREE-20260813-001.md`;
- exact base/head, changed files, screenshots or HTML evidence, tests and CI;
- final Issue/PR marker `READY_FOR_COORDINATOR_QA`.

Do not merge.