# HANDOFF — Parallel implementation workstreams

HANDOFF-ID: `HANDOFF-PARALLEL-WORKSTREAMS-20260813-004`  
DATE: `2026-08-13`  
REPOSITORY: `fitera2024-rgb/excel-transform-1c`  
PARENT IMPLEMENTATION PR: `#4`  
STARTING IMPLEMENTATION HEAD: `e96fb403da7b96a5707ba131cb141788fe27bde3`  
STATUS: `OWNER_ACCEPTED_A_PLUS_D / THREE_STREAMS_READY / NO_MERGE`  
SAFETY: `NO ADO / NO LIVE WRITE`

## Owner decision

The owner accepted the proposed acceleration plan:

- sequence `A + D` for ERP mapping: repair parser first, preserve exact-first, then use explicit hierarchical user selection for the small remainder;
- split implementation across three independent chat/Codex agents;
- keep this coordinator chat as the only integration and decision point;
- run independent combined QA only after all three streams are integrated.

## Shared start point

All implementation branches were created from:

`e96fb403da7b96a5707ba131cb141788fe27bde3`

They target:

`feat/v1-excel-transform-preview`

No agent writes directly to the parent branch and no agent merges its own PR.

## Stream A — ERP hierarchy parser

- Issue: `#8`
- Branch: `fix/erp-article-hierarchy-parser`
- Task Contract: `governance/tasks/WORK-ERP-ARTICLE-HIERARCHY-PARSER-20260813-001.md`
- Contract head: `30f709ed2319d0ee8217f92d4f7f067e9fd3dc8e`
- Risk: `L`
- Primary files: ERP reference parser and parser-specific tests
- Research authority: Draft PR `#6`, head `14bd2c3020043a1affd0adace81a06775bed660b`

## Stream B — Large and protected Excel intake

- Issue: `#7`
- Branch: `perf/streaming-protected-excel`
- Task Contract: `governance/tasks/CR-LARGE-PROTECTED-EXCEL-20260813-001.md`
- Contract head: `cdde336e9629fe49108a9819d54e4c2679525289`
- Risk: `M`
- Primary files: Excel/upload adapter, narrow protected-OOXML adapter, upload workflow/tests

## Stream C — Inline attention and ERP hierarchy UX

- Issue: `#9`
- Branch: `feat/inline-attention-erp-tree`
- Task Contract: `governance/tasks/CR-INLINE-ATTENTION-ERP-TREE-20260813-001.md`
- Contract head: `e54ebc6a498f42f504fe5f6cb98353b8b09e753a`
- Risk: `M`
- Primary files: run template, UI static assets, UI tests

## Independent combined QA

- Issue: `#10`
- Status: blocked until all three stream PRs are `READY_FOR_COORDINATOR_QA`
- QA may not modify implementation code
- QA starts only from the exact combined head recorded by the coordinator

## Integration order

Development is parallel. Integration is sequential:

1. ERP hierarchy parser;
2. large/protected Excel intake;
3. inline attention and ERP hierarchy UX;
4. full CI;
5. independent combined QA;
6. Owner UX Smoke;
7. parent PR merge only after explicit owner acceptance.

## Cross-stream rule

Each agent owns its declared files. If another stream requires a file change, the agent must first post:

`CROSS_STREAM_DEPENDENCY`

with the exact required DTO, endpoint, helper or behavior in its GitHub Issue. Silent cross-stream edits are not accepted.

## Agent handoff rule

Every implementation agent must leave all evidence in GitHub:

- Draft PR targeting `feat/v1-excel-transform-preview`;
- exact base and head;
- changed files;
- tests and CI;
- branch-specific handoff;
- final marker `READY_FOR_COORDINATOR_QA`;
- no merge.

The owner should not manually transfer technical reports between agents and the coordinator.