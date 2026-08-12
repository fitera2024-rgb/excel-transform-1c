# HANDOFF — Owner UX: organization hierarchy, open access and all-year period

HANDOFF-ID: `HANDOFF-OWNER-UX-ORG-PERIOD-20260813-003`  
DATE: `2026-08-13`  
REPOSITORY: `fitera2024-rgb/excel-transform-1c`  
PR: `#4`  
BRANCH: `feat/v1-excel-transform-preview`  
RISK: `M`  
STATUS: `OWNER_DECISION_IMPLEMENTED / CI_REQUIRED / OWNER_UX_SMOKE_CONTINUE / NO_MERGE`  
SAFETY: `NO ADO / NO LIVE WRITE`

## Owner observations

During Owner UX Smoke:

- the scenario selector is visible;
- the organization selector is technically usable but a single flat list of 357 nodes is inconvenient;
- the separate `Область доступа` card is unnecessary for this local converter;
- all users of the local installation may access the entire organization tree;
- the period selector needs an explicit checkbox for all twelve months.

## Accepted owner decisions

### Organization access

The previous delegation/effective-access behavior is superseded for V1.

- no separate access-rights screen;
- no user-specific organization filtering;
- all locally loaded organizations and nodes are available to everyone;
- enterprise RBAC and delegated subtrees are outside the local-converter scope.

### Hierarchical organization choice

The organization context is selected in two steps:

1. select an upper/root branch;
2. keep that upper node selected or choose any descendant organization, department or CFO in its subtree.

Selecting an upper branch makes its complete subtree available. The service still does not guess the correct `ПС`/`Б_ПС`/legal-entity branch.

### Period

The UI contains a checked-by-default `Весь год` checkbox.

- checked: preview/export view uses all twelve months;
- unchecked: one or more months must be selected;
- unchecked with no selected month: processing does not start and a clear Russian message is shown;
- internal transformation still produces all twelve months, including zero values.

## Implementation

- removed the `Область доступа` card and delegation action from normal UI;
- legacy local delegation state is cleared on application startup so an earlier Draft cannot hide nodes;
- added a root-branch selector and a descendant-node selector;
- the upper node is selected by default after choosing a root, while all descendants remain available;
- added explicit `Весь год` checkbox and month enable/disable behavior;
- preserved the existing scenario selector;
- added server-side validation for period mode;
- added UI regression coverage for open access, hierarchy, scenarios, all-year and month-only modes.

## Feature Baseline result

- `ORG-002`: `CHANGED_AUTHORIZED` — two-stage hierarchy selector;
- `PERIOD-001`: `CHANGED_AUTHORIZED` — explicit all-year checkbox;
- `ACCESS-001..004`: `REMOVED_AUTHORIZED` — delegation/effective-access removed from V1;
- `UX-004`, `UX-005`: added as accepted invariants.

## Remaining Owner UX Smoke

1. update/restart the latest PR head while keeping `runtime/local.db`;
2. confirm counters `271 / 357 / 12`;
3. choose a top branch and confirm only its subtree appears in the second selector;
4. choose the top node itself, then optionally a child node;
5. confirm `Весь год` is checked by default and month checkboxes are inactive;
6. uncheck `Весь год` and confirm months become selectable;
7. select scenario/year, load budget Excel, inspect preview/issues, apply one correction and export.

PR remains Draft. Merge is not authorized before explicit owner acceptance.
