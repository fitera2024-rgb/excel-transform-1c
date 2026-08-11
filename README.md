# excel-transform-1c

Лёгкий внутренний сервис для цепочки:

`Excel → validation → transformation → preview → later ADO DRY RUN → controlled 1C write`.

## Current status

`DISCOVERY / PRODUCT CONTRACT + USER FLOW / COORDINATOR HANDOFF READY`

До принятия User Flow владельцем реализация не начинается.

## Start here

1. `governance/handoffs/HANDOFF-COORDINATOR-20260811-001.md` — полный handoff discovery и принятых решений.
2. `docs/PRODUCT.md`
3. `docs/USER_FLOW.md`
4. `governance/DECISIONS.md`
5. `governance/FEATURE_BASELINE.md`
6. `governance/ACTIVE_WORK.md`
7. `docs/ARCHITECTURE.md`
8. `AGENTS.md` — правила для Codex

## Product principle

Новый сервис — быстрый рабочий помощник: максимум корректных данных сохраняется в preview, локальные проблемы показываются в Реестре ошибок/внимания и не должны превращаться в тяжёлые многоходовые блокировки.

## Boundary

OPIU используется только как visual/UX reference и источник отдельных проверенных reliability/safety patterns. Новый сервис не является fork OPIU.

Первая vertical slice не пишет в 1С/БД. Live write по умолчанию запрещён и требует отдельного owner gate.
