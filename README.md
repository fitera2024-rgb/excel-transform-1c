# excel-transform-1c

Лёгкий внутренний сервис для цепочки:

`Excel → validation → transformation → preview → later ADO DRY RUN → controlled 1C write`.

## Current status

`DISCOVERY / PRODUCT CONTRACT + USER FLOW`

До принятия User Flow владельцем реализация не начинается.

## Start here

1. `docs/PRODUCT.md`
2. `docs/USER_FLOW.md`
3. `docs/ARCHITECTURE.md`
4. `governance/DECISIONS.md`
5. `governance/FEATURE_BASELINE.md`
6. `governance/ACTIVE_WORK.md`
7. `AGENTS.md` — правила для Codex

## Boundary

OPIU используется только как visual/UX reference и источник проверенных reliability/safety patterns. Новый сервис не является fork OPIU.

Live write в 1С/БД по умолчанию запрещён и требует отдельного owner gate.
