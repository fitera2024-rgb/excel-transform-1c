# Active Work

STATUS: `PRODUCT_ACCEPTED / USER_FLOW_OWNER_REFINED / THREE_PARALLEL_STREAMS_ACTIVE / DRAFT_PR_4 / NO_LIVE_WRITE`

## Current phase

Первая vertical slice уже реализована в Draft PR `#4`:

`Excel → structural detection → validation → exact ERP mapping/manual correction → 12-month normalization → maximum preview → error registry → export`

Owner UX Smoke подтвердил базовую работоспособность и выявил следующие улучшения перед финальным gate:

- исправить системный дефект разбора иерархии ERP-статей;
- оптимизировать приём больших и защищённых Excel;
- перенести исправление `Требует внимания` к самой проблемной строке;
- выбирать ERP-код по иерархии, а не из плоского списка.

## Accepted owner decisions

Владелец принял ускоренный план и последовательность `A + D`:

- сначала исправить ERP parser;
- exact full path остаётся единственным автоматическим правилом;
- небольшой остаток разрешается явным иерархическим выбором;
- fuzzy/typo/case/name-only autofix не включается;
- `Удалить` / `!!!Удалить` не скрываются;
- работа распределяется на три независимых агента;
- этот координаторский контур остаётся единственной точкой интеграции;
- финальный combined QA выполняется отдельно после интеграции всех трёх потоков.

Exact coordination handoff:

`governance/handoffs/HANDOFF-PARALLEL-WORKSTREAMS-20260813-004.md`

## Git authority

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Parent branch: `feat/v1-excel-transform-preview`.
- Parent Draft PR: `#4`, open, not merged.
- Last fully tested implementation head before split: `e96fb403da7b96a5707ba131cb141788fe27bde3`.
- Coordination handoff commit before this update: `8666ea3ed800f56704b1ddb894d2bc6df3774fbf`.
- Accepted product base: `836b3154c4c81ebc9c0ec3f8ef895afee5d47098`.
- ADO/live write: not implemented and not performed.

## Parallel stream A — ERP hierarchy parser

- Issue: `#8`.
- Risk: `L`.
- Branch: `fix/erp-article-hierarchy-parser`.
- Task Contract: `governance/tasks/WORK-ERP-ARTICLE-HIERARCHY-PARSER-20260813-001.md`.
- Exact contract head: `30f709ed2319d0ee8217f92d4f7f067e9fd3dc8e`.
- Research authority: Draft PR `#6`, exact head `14bd2c3020043a1affd0adace81a06775bed660b`.
- Status: `READY_FOR_AGENT_START`.

## Parallel stream B — Large/protected Excel intake

- Issue: `#7`.
- Risk: `M`.
- Branch: `perf/streaming-protected-excel`.
- Task Contract: `governance/tasks/CR-LARGE-PROTECTED-EXCEL-20260813-001.md`.
- Exact contract head: `cdde336e9629fe49108a9819d54e4c2679525289`.
- Status: `READY_FOR_AGENT_START`.

## Parallel stream C — Inline attention and ERP hierarchy UX

- Issue: `#9`.
- Risk: `M`.
- Branch: `feat/inline-attention-erp-tree`.
- Task Contract: `governance/tasks/CR-INLINE-ATTENTION-ERP-TREE-20260813-001.md`.
- Exact contract head: `e54ebc6a498f42f504fe5f6cb98353b8b09e753a`.
- Status: `READY_FOR_AGENT_START`.

## Combined QA

- Issue: `#10`.
- Status: `BLOCKED_UNTIL_THREE_STREAMS_READY`.
- QA may not change implementation code.
- QA starts only from the exact combined head recorded after sequential integration.

## Integration order

Development is parallel; integration is sequential:

1. parser stream;
2. large/protected upload stream;
3. inline attention/ERP hierarchy UX stream;
4. full GitHub CI;
5. independent combined QA;
6. Owner UX Smoke;
7. merge only after explicit owner acceptance.

## Last verified baseline before new stream code

GitHub Actions `V1 CI`, run `31644007981`:

- compileall — PASS;
- unit — `14 passed`;
- integration — `19 passed`;
- UI smoke — `11 passed`;
- full regression — `44 passed`;
- no tracked `.xlsx/.xls/.xlsm` — PASS.

This evidence applies only to `e96fb403...`. Every new stream must provide fresh tests and CI.

## Cross-stream boundary

An agent must not silently edit another stream's primary files. Required cross-stream work is first recorded in its Issue as:

`CROSS_STREAM_DEPENDENCY`

with the exact DTO, endpoint, helper or behavior required.

## Current next action

`START_THREE_AGENT_TASKS`

Each agent opens a Draft PR targeting `feat/v1-excel-transform-preview`, leaves exact Git/test/handoff evidence and finishes with:

`READY_FOR_COORDINATOR_QA`

No agent merges.

## Forbidden

- merge while Issues `#7`, `#8`, `#9` or combined QA `#10` are incomplete;
- ADO connection or live write;
- TEST/PROD write;
- direct SQL write into 1C;
- real business Excel/reference files or password in Git;
- fuzzy/typo/case/name-only automatic ERP assignment;
- filename-based source detection;
- password persistence;
- reintroduction of local access-rights complexity;
- platform/multi-tenant/enterprise expansion.