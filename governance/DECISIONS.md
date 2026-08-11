# Decisions

Принятые решения не переписываются молча. Изменение принятого решения фиксируется новой записью с указанием supersedes.

## DEC-BOOT-001 — Project boundary

STATUS: `ACCEPTED`

- Новый сервис создаётся отдельным репозиторием, не fork/branch OPIU.
- OPIU используется только как visual/UX reference и источник проверенных reliability/safety patterns.
- R005, R001, Rules Engine и source-proof UI не входят в новый сервис по умолчанию.

## DEC-BOOT-002 — Delivery order

STATUS: `ACCEPTED`

- Сначала Product Contract и User Flow.
- Первая vertical slice: Excel → validation → transformation → preview.
- ADO/write проектируется позже отдельным high-risk этапом.
- Production live-write только после отдельного owner gate.
