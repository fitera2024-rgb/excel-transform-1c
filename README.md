# excel-transform-1c

Лёгкий внутренний сервис для цепочки:

`Excel → validation → transformation → preview → later ADO DRY RUN → controlled 1C write`.

## Практическое назначение

Сервис создаётся как **локальная внутренняя утилита для повторяемого преобразования ограниченного набора бюджетных Excel-таблиц в согласованный формат для 1С**.

Это не универсальная интеграционная платформа, не multi-tenant SaaS и не глобальный сервис. Основной результат — корректно преобразованные данные, понятный preview и файл/набор данных в формате, пригодном для дальнейшей загрузки в 1С.

ADO и фактическая запись в 1С являются отдельным последующим этапом и не должны усложнять первую версию конвертера.

## Current status

`PRODUCT CONTRACT ACCEPTED / USER FLOW ACCEPTED / IMPLEMENTATION TASK PREPARATION / NO LIVE WRITE`

Владелец принял User Flow первой vertical slice. Разрешена подготовка реализации `Excel → validation → ERP mapping → user corrections → 12-month normalization → preview → export`.

## Start here

1. `governance/handoffs/HANDOFF-OWNER-DECISIONS-20260812-002.md` — финальный пакет owner decisions и принятие User Flow.
2. `governance/handoffs/HANDOFF-EXCEL-LOGIC-20260812-001.md` — карта реальных Excel, ERP-справочников и доказательств.
3. `docs/PRODUCT.md`
4. `docs/USER_FLOW.md`
5. `governance/DECISIONS.md`
6. `governance/FEATURE_BASELINE.md`
7. `governance/ACTIVE_WORK.md`
8. `docs/ARCHITECTURE.md`
9. `AGENTS.md` — правила для Codex
10. `docs/SERVICE_FACTORY_SKILLS_AND_PLUGINS_PLAN_RU.md` — справочный план reusable Skills и tooling; не является разрешением раздувать scope.

## Product principle

Новый сервис — быстрый рабочий помощник: максимум корректных данных сохраняется в preview, локальные проблемы показываются в Реестре ошибок/внимания и не должны превращаться в тяжёлые многоходовые блокировки.

## Принцип соразмерности

Не строить безопасность, governance и архитектурные слои ради самих слоёв. Для локального конвертера применяются только меры, которые прямо защищают корректность преобразования, исходные данные, повторяемость результата или будущую фактическую запись в 1С.

Любой новый контроль должен быть связан с конкретным реальным риском и не иметь более простого решения. Иначе он откладывается или не входит в scope.

## Boundary

OPIU используется только как visual/UX reference и источник отдельных проверенных reliability/safety patterns. Новый сервис не является fork OPIU.

Первая vertical slice не пишет в 1С/БД. Live write по умолчанию запрещён и требует отдельного owner gate.
