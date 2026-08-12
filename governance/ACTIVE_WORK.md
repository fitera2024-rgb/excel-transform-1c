# Active Work

STATUS: `PRODUCT_ACCEPTED / USER_FLOW_ACCEPTED / V1_IMPLEMENTATION_ACTIVE / NO_LIVE_WRITE`

## Current phase

Discovery, Product Contract and User Flow V1 завершены и приняты владельцем.

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

## Implementation task

GitHub Issue: `#2 — [M] V1: Excel → validation → ERP mapping → preview → export`

Exact task contract:

`governance/tasks/CODEX-TASK-EXCEL-V1-20260812-001.md`

Risk: `M`.

## Start gate

Implementation must not start until:

1. Draft PR #1 is reviewed and merged;
2. exact merged product head is pinned in the task contract/Issue #2;
3. Codex creates `feat/v1-excel-transform-preview` from that exact commit.

После выполнения start gate дополнительные Product/UX вопросы владельцу для начала V1 не требуются.

## Current next action

`IMPLEMENT_ISSUE_2_AND_OPEN_DRAFT_PR`

Product PR #1 merged. Exact implementation base:
`836b3154c4c81ebc9c0ec3f8ef895afee5d47098`.

Текущая реализация выполняется только в `feat/v1-excel-transform-preview`.
После Draft implementation PR требуются coordinator QA и Owner UX Smoke;
самостоятельный merge запрещён.

## Forbidden

- ADO connection;
- live write;
- TEST/PROD write;
- direct SQL write в 1С;
- старт Codex от непроверенного/непринятого base;
- реальные business Excel/справочники в Git;
- fuzzy/typo/case auto-match;
- самостоятельный merge Codex;
- platform/multi-tenant/enterprise expansion;
- переоткрытие ACCEPTED решений без нового evidence или owner decision.

## Git state

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Product branch: `coord/proportional-safety-local-converter`.
- Product PR: `#1`, merged.
- Implementation Issue: `#2`, open and in implementation.
- Product head before this Active Work update: `b4d263b2b2c4dda94621c0b88bc786e3edc77288`.
- Current exact head: latest head of PR #1.
- Product implementation: active in `feat/v1-excel-transform-preview`.
- ADO/live write: not performed.
