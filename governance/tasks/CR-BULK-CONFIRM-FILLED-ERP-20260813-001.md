# CR — Bulk confirmation of filled ERP mappings

CR-ID: `CR-BULK-CONFIRM-FILLED-ERP-20260813-001`
RISK: `M`
STATUS: `OWNER_ACCEPTED / READY_FOR_IMPLEMENTATION / NO_MERGE`
ISSUE: `#16`
REPOSITORY: `fitera2024-rgb/excel-transform-1c`
START BASE: `6f2f0aa1121093f51b229a7fc4e402b13166602f`
WORK BRANCH: `feat/bulk-confirm-filled-erp`
TARGET BRANCH: `integration/v1-approved-streams`
PARENT INTEGRATION PR: `#15`
SAFETY: `NO ADO / NO LIVE WRITE`

## Read before implementation

1. `AGENTS.md`
2. `docs/PRODUCT.md`
3. `docs/USER_FLOW.md`
4. `docs/ARCHITECTURE.md`
5. `governance/DECISIONS.md`
6. `governance/FEATURE_BASELINE.md`
7. `governance/ACTIVE_WORK.md`
8. Issue `#16`
9. Draft integration PR `#15`
10. `governance/handoffs/HANDOFF-INTEGRATED-V1-STREAMS-20260813-001.md`
11. Inline UX handoff for PR `#11`

Before changes, verify:

```text
git branch --show-current
# feat/bulk-confirm-filled-erp

git rev-parse HEAD
# exact task-contract head on this branch, descended from 6f2f0aa...
```

Do not modify files until the branch and contract head match GitHub.

## Owner UX decision

Add one page-level confirmation for all already fully filled ERP mappings:

`Подтверждаю все заполненные ERP-сопоставления`

The user must not tick the same ERP confirmation separately for every eligible source row.

## Required business behavior

### Eligibility

A source row is eligible for bulk confirmation only when the current visible ERP selection is complete and unambiguous:

`Тип расходов → Группа расходов → Статья → ERP-код`.

Rules:

- all values come from the loaded ERP catalog;
- the selected code must belong to the selected exact hierarchy path;
- an empty hierarchy level is valid only when represented explicitly by the existing reversible UI sentinel and decoded back to the exact empty business value;
- placeholder, missing, conflicting or ambiguous selections are not eligible;
- no fuzzy, typo, case-only or name-only selection is allowed;
- bulk confirmation never chooses or changes a code by itself.

### Page-level control

Show above the editable attention groups:

- checkbox: `Подтверждаю все заполненные ERP-сопоставления`;
- counter: `Будет подтверждено: N строк`;
- action: `Применить все заполненные`.

When `N = 0`:

- checkbox/action are disabled or the action is unavailable;
- show a clear business message that no fully filled ERP mappings are ready for confirmation.

### Bulk apply

After explicit page-level confirmation and one bulk action:

- apply only the eligible rows shown in the current run;
- update all 12 monthly records derived from each eligible source row;
- do not perform a full rerun;
- preserve unrelated unresolved and read-only reasons on the same rows;
- leave ineligible rows visible and individually editable;
- keep `rerun_count` unchanged;
- persist reusable manual mappings only under the existing key:
  `вид отчёта → тип расходов → группа расходов → исходная статья`;
- the action is idempotent and must not create duplicate mappings or duplicate updates.

### Explicit exclusions

Bulk ERP confirmation must not confirm or change:

- tax;
- department;
- CFO;
- amount;
- monthly Excel errors;
- negative amount attention;
- reporting-unit conflicts;
- any other read-only issue.

Individual row confirmation and correction must remain available and unchanged.

## Implementation boundaries

Primary ownership:

- `src/excel_transform_1c/ui/templates/run.html`;
- `src/excel_transform_1c/ui/static/run.js`;
- minimal UI/app workflow support required for one allowlisted bulk action;
- tests covering bulk selection and application;
- one implementation handoff.

Do not change:

- ERP parser semantics;
- protected/streaming intake behavior;
- reference import rules;
- manual mapping key semantics;
- organization/scenario/period decisions;
- export schema;
- ADO/1C/live-write paths.

If a server endpoint or application workflow change is needed, keep it narrow, allowlisted and idempotent. Business Core must remain independent of UI and filesystem paths.

## Required tests

Use synthetic fixtures only.

Cover at least:

1. master checkbox appears only when there are eligible filled ERP mappings;
2. counter equals the number of eligible source rows, not monthly records;
3. one source row with 12 months counts as one row;
4. incomplete/placeholder/ambiguous selections are excluded;
5. explicit empty hierarchy levels remain eligible when the exact empty value is selected;
6. master checkbox does not alter selections before submit;
7. bulk action updates every month for every eligible source row;
8. no full rerun and `rerun_count` remains unchanged;
9. unrelated unresolved/read-only reasons remain visible;
10. individual confirmation still works;
11. repeated bulk apply is idempotent and creates no duplicate manual mappings;
12. no tax/department/CFO/read-only field is silently confirmed;
13. current organization hierarchy, scenario selector, `Весь год`, preview and export remain present;
14. full regression suite and JavaScript syntax check.

## Deliverables

- implementation and tests in `feat/bulk-confirm-filled-erp`;
- Draft PR to `integration/v1-approved-streams`;
- handoff:
  `governance/handoffs/HANDOFF-BULK-CONFIRM-FILLED-ERP-20260813-001.md`;
- exact base/head, changed files, tests and GitHub Actions run;
- final marker:
  `READY_FOR_COORDINATOR_QA`;
- no merge.

After integration, repeat affected combined QA and Owner UX Smoke. The current QA result cannot approve this new UX until the exact updated combined head is tested.

`NO ADO / NO LIVE WRITE / NO MERGE`.
