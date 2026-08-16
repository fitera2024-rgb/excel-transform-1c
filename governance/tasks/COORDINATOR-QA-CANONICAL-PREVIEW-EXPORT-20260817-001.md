# COORDINATOR QA — Canonical Preview/Export Integration

QA-ID: `COORDINATOR-QA-CANONICAL-PREVIEW-EXPORT-20260817-001`

RISK: `L`

STATUS: `WAITING_FOR_CODEX_HANDOFF / NO_CODE_CHANGE / NO_MERGE / NO_RELEASE / NO_LIVE_WRITE`

## Trigger

Start independent QA only after Issue #27 and the canonical Draft PR contain:

`READY_FOR_COORDINATOR_QA_CANONICAL_INTEGRATION`

and the exact final head is pinned.

## Exact authority

- Integration branch: `integration/canonical-preview-export-v1`.
- Mandatory ancestor A: `c713cee112e4b935b3a5b2c319d23fc6cbf180cb`.
- Mandatory ancestor B: `77645317b673b2e57dea803410126a61cdaf6d83`.
- Owner gate handoff: `governance/handoffs/HANDOFF-OWNER-GATE-CANONICAL-PREVIEW-EXPORT-20260817-001.md`.
- Codex contract: `governance/tasks/CODEX-TASK-CANONICAL-PREVIEW-EXPORT-INTEGRATION-20260817-001.md`.

Any head movement after QA begins invalidates the result and requires repeat QA.

## QA responsibilities

### 1. Git lineage

Verify:

- exact branch and final head;
- both mandatory SHAs are ancestors;
- the semantic integration preserved history;
- no squash, rebase, force rewrite or deceptive synthetic provenance;
- conflict-discovery PR #26 is resolved by the canonical lineage;
- source PR #24 and PR #25 were not independently merged to `main`.

### 2. Conflict audit

Inspect every overlap recorded in the Codex handoff and independently check at least:

- Excel adapter;
- persistence;
- application service;
- models;
- indicator matching and OPIU resolver precedence;
- UI upload/run flows;
- export and package documentation;
- focused tests from both parents.

Reject the integration if an overlapping business file was resolved by unexplained whole-file `ours` or `theirs` selection.

### 3. Product contract

Confirm that Product, User Flow, Architecture, Decisions, Feature Baseline and Active Work consistently describe:

- full BDR with KPI, revenue and expenses;
- prepared budgets;
- annual and monthly Intalev OPIU;
- exact disclosure-group/article/formula-source resolver;
- three-sheet export;
- latest access/delegation owner decision;
- narrow domain rules boundary;
- no ADO/live write.

### 4. Functional preservation

Verify that the combined head preserves:

- structural and content-based Excel detection;
- protected/legacy intake and exact original/working-copy separation;
- full BDR and exact saved values;
- KPI independent of expense article;
- revenue and expense context;
- organization/CFO/channel/source pointers;
- exact ERP and OPIU rule semantics;
- unresolved attention behavior without guessing;
- manual/bulk confirmations and restart persistence;
- three-sheet export;
- Windows short runtime path.

### 5. Automated verification

Review exact commands and independently confirm CI evidence for:

- compileall;
- unit tests;
- integration tests;
- UI tests;
- full regression;
- JavaScript syntax;
- diff hygiene;
- no tracked owner Excel/MXL;
- wheel resources;
- Windows offline package;
- HTTP owner flow, restart and stop;
- ZIP integrity and digest.

No test deletion, lowered assertion or unexplained skip may be accepted.

### 6. Financial and reconciliation checks

Review available source-reconciliation evidence. At minimum:

- preserve the zero-mismatch АЮ evidence already accepted from PR #25;
- confirm the combined resolver does not alter row-level values or context silently;
- separate source Excel errors and reference gaps from service defects;
- require equivalent reconciliation for ПВ/ПС when they are included in the Owner Smoke evidence and the source files are available outside Git.

### 7. Safety audit

Search the final diff and runtime paths for:

- ADO;
- ODBC;
- SQL write;
- 1C write;
- live-write flags or hidden endpoints;
- real workbooks/MXL;
- passwords, tokens, connection strings and private absolute paths;
- fuzzy/contains/typo/case-only matching;
- universal Rules Engine or normal-user technical rules UI.

## Allowed QA result

Return exactly one:

- `CHANGES_REQUIRED_CANONICAL_INTEGRATION`;
- `READY_FOR_OWNER_UX_SMOKE_CANONICAL_PREVIEW_EXPORT`.

QA does not merge, release or change implementation code.

## Owner UX Smoke gate

When technically ready, give the owner one exact package and business-only steps:

1. start the service;
2. load a real full BDR;
3. inspect KPI, revenue and expense preview;
4. verify one OPIU indicator resolution and one unresolved case;
5. make one individual correction and one supported bulk confirmation;
6. export and inspect all three sheets;
7. restart and verify persistence;
8. stop the service.

Merge remains blocked until the owner explicitly accepts that exact package/head.
