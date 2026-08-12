# Active Work

STATUS: `PRODUCT_ACCEPTED / USER_FLOW_ACCEPTED / IMPLEMENTATION_READY / EXACT_PRODUCT_BASE_PINNED`

## Current phase

Discovery, Product Contract, Architecture Light boundaries and User Flow V1 завершены и приняты владельцем.

Product/governance PR #1 merged.

Актуальные handoff:

- `governance/handoffs/HANDOFF-OWNER-DECISIONS-20260812-002.md` — финальный пакет owner decisions;
- `governance/handoffs/HANDOFF-EXCEL-LOGIC-20260812-001.md` — evidence, карты Excel и ERP-справочников.

## Accepted V1

Первая vertical slice:

`Excel → structural detection → validation → exact ERP mapping/manual correction → 12-month normalization → maximum preview → error registry → export`

Ключевые принятые решения:

- local converter, не platform;
- prepared expense range as input;
- 12 месяцев, включая нули;
- cached formula values, без Excel recalculation;
- continue with attention;
- exact ERP mapping, no fuzzy/autofix;
- local persistent scenarios, включая добавленные пользователем;
- `ПЛАН_2026` = `ПЛАН 2026`, stable local scenario ID;
- year + optional month filter;
- manual organization branch selection per run;
- all organization nodes visible, no guessed status/type filtering;
- delegation on any tree node and whole subtree;
- reusable mapping key = report type + full article path;
- negative amounts preserved with attention;
- nodes/records named `Удалить` are not auto-excluded;
- User Flow accepted.

## Implementation authority

GitHub Issue:

`#2 — [M] V1: Excel → validation → ERP mapping → preview → export`

Exact task contract:

`governance/tasks/CODEX-TASK-EXCEL-V1-20260812-001.md`

Risk: `M`.

Exact implementation base:

`836b3154c4c81ebc9c0ec3f8ef895afee5d47098`

Target implementation branch:

`feat/v1-excel-transform-preview`

## Start gate — COMPLETED

- PR #1 reviewed and merged;
- exact merged product commit pinned in Issue #2 and task contract;
- Product Contract and User Flow accepted;
- no additional owner Product/UX decision is required to start V1.

Codex must create the target branch exactly from the pinned implementation base, keep its implementation PR Draft and not merge it.

## Current next action

`START_CODEX_FROM_ISSUE_2`

После Codex:

1. получить Draft implementation PR;
2. проверить exact base/head, diff, tests and handoff;
3. проверить Feature Baseline;
4. выполнить independent coordinator review;
5. провести Owner UX Smoke до release.

## Forbidden

- ADO connection;
- live write;
- TEST/PROD write;
- direct SQL write в 1С;
- старт Codex от другого base;
- реальные business Excel/справочники в Git;
- fuzzy/typo/case auto-match;
- самостоятельный merge Codex;
- platform/multi-tenant/enterprise expansion;
- переоткрытие ACCEPTED решений без нового evidence или owner decision.

## Git state

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Product PR: `#1`, merged.
- Product merge commit: `836b3154c4c81ebc9c0ec3f8ef895afee5d47098`.
- Implementation Issue: `#2`, ready for Codex after exact authority update.
- Implementation branch: not created yet; Codex must create it from the pinned base.
- Product implementation: not started.
- ADO/live write: not performed.
