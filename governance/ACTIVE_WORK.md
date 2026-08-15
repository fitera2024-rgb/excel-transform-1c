# Active Work

STATUS: `THREE_SHEET_EXPORT_READY / AUTO_ARTICLE_INDICATOR_MATCHING_READY_FOR_CODEX / DRAFT / NO_MERGE / NO_LIVE_WRITE`

## Current vertical slice

`Built-in references → content-based Excel preparation → prepared budget or Intalev OPIU → exact ERP/tax/CFO decisions → automatic direct article-to-indicator matching → 12-month preview → three-sheet XLSX export`

## Canonical implementation

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Working branch: `feat/final-owner-smoke-fitera-v2`.
- Draft PR: `#23`, not merged.
- Current head after task registration: `f11c1893240e06790a40481bdc3bc2b7be00fb9b`.
- Three-sheet export already preserves `OPIU Light` and adds `ОПИУ` plus `Показатели`.

## Current owner decision

Normal user must not manage technical Rules manually.

When a loaded classifier contains a direct correspondence `статья → показатель`, the service must find and apply one unique exact match automatically. Missing or ambiguous matches stay visible as `Требует внимания`; fuzzy, typo and case-only matching remain forbidden.

## Active registry

- Work registry: `governance/tasks/WORK-REGISTRY-AUTO-ARTICLE-INDICATOR-20260815-001.md`.
- Codex implementation task: `governance/tasks/CODEX-TASK-AUTO-ARTICLE-INDICATOR-20260815-001.md`.
- Coordinator QA task: `governance/tasks/COORDINATOR-QA-AUTO-ARTICLE-INDICATOR-20260815-001.md`.

## Responsibility split

### Codex

- direct classifier import and persistence;
- exact matcher `article → indicator`;
- automatic filling and aggregation of `Показатели`;
- simplified UI without required Rules workflow;
- tests, handoff and green CI;
- final marker `READY_FOR_COORDINATOR_QA_AUTO_INDICATORS`.

### ChatGPT coordinator

- Product Contract and acceptance boundaries;
- Git/PR/diff/tests/handoff review;
- ambiguity and financial-semantics audit;
- example ADO verification;
- Windows package smoke;
- Owner UX Smoke and final package delivery.

## Forbidden

- merge without owner acceptance;
- ADO/ODBC/1C/live write;
- fuzzy, typo, case-only or contains matching;
- invented indicators, channels or reference codes;
- real Excel, passwords or runtime databases in Git;
- removal of the legacy `OPIU Light` sheet.
