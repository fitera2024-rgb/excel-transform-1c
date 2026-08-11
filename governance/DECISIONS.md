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

## DEC-PRODUCT-001 — Light error handling

STATUS: `ACCEPTED`

- Новый сервис — быстрый рабочий помощник, а не контрольный шлюз.
- Основной принцип первой версии: обработать максимум корректных данных и собрать проблемы в понятный Реестр ошибок.
- Локальная ошибка не блокирует обработку всего файла; пропускается только минимально необходимая проблемная единица данных.
- Пользовательские состояния: `ОК`, `Требует внимания`, `Пропущено`.
- Частичный полезный результат разрешён.
- Полная остановка допускается только когда технически невозможно продолжать обработку вообще.
- Более строгие ограничения для ADO/live-write определяются отдельно и не переносятся автоматически на Excel → validation → transformation → preview.
