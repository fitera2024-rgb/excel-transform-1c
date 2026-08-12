# Active Work

STATUS: `PRODUCT_ACCEPTED / USER_FLOW_ACCEPTED / CODEX_DISPATCH_RECORDED / WAITING_FOR_DRAFT_PR`

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
- no additional owner Product/UX decision is required to start V1;
- explicit Codex execution directive posted in Issue #2.

Codex must create the target branch exactly from the pinned implementation base, keep its implementation PR Draft and not merge it.

## Coordinator verification authority

Coordinator QA Issue:

`#3 — [COORD-QA] Проверить Draft PR реализации V1 по Issue #2`

Exact coordinator contract:

`governance/tasks/COORDINATOR-QA-V1-20260812-001.md`

Trigger: появление Draft implementation PR, связанного с Issue #2.

Координатор обязан независимо проверить:

- exact base/head/branch;
- полный diff и changed files;
- tests/CI/reproducibility;
- synthetic fixtures and absence of real business data;
- Feature Baseline regressions;
- отсутствие ADO/live write/direct SQL;
- отсутствие fuzzy/autofix и platform expansion;
- Codex handoff;
- готовность к Owner UX Smoke.

## Current next action

`WAIT_FOR_CODEX_DRAFT_PR`

После появления Draft PR:

1. активировать Issue #3;
2. проверить exact base/head, diff, tests and handoff;
3. проверить Feature Baseline;
4. при проблемах запросить изменения в PR;
5. при технической готовности вернуть владельцу Owner UX Smoke;
6. не merge-ить implementation PR до завершения smoke.

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
- Implementation Issue: `#2`, ready and explicitly dispatched to Codex.
- Coordinator QA Issue: `#3`, waiting for implementation Draft PR.
- Implementation branch: not observed yet; Codex must create it from the pinned base.
- Product implementation: no Draft PR observed yet.
- ADO/live write: not performed.
