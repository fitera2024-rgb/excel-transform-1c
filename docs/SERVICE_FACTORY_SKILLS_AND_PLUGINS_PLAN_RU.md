# Service Factory — план Skills, плагинов и инструментов

STATUS: `HANDOFF / PLANNED / NOT_IMPLEMENTATION_APPROVAL`
DATE: `2026-08-11`
REPOSITORY: `fitera2024-rgb/excel-transform-1c`

Назначение: сохранить переданный владельцу план повторно используемой фабрики сервисов для следующего проекта `Excel → transformation → ADO → 1C`. Этот документ является частью coordinator handoff. Он не разрешает начинать реализацию до принятия Product Contract и User Flow.

## 1. Принцип

Не переносить OPIU целиком. Переиспользовать только удачные паттерны и отдельные Skills. Новый сервис строится как OPIU Light: быстрый пользовательский помощник, минимум технического UX, максимум полезного результата.

Базовая схема:

`Owner → ChatGPT coordinator → GitHub → Codex → PR/tests/handoff → coordinator review → owner gate where required`

Git хранит контракты, решения, задачи, handoff и доказательства. Владелец не должен вручную переносить технические задания/отчёты между ChatGPT и Codex, если это можно сделать через Git.

## 2. План reusable Skills

### 2.1 `service-factory-coordinator`

Назначение: вести новый сервис от Product Contract до release gate.

Должен уметь:
- читать Product/User Flow/Decisions/Baseline/Active Work и Git state;
- классифицировать изменение по риску;
- формировать WORK/CR/acceptance/test gates;
- передавать точный Git-visible Codex Task Contract;
- после Codex проверять PR/diff/tests/handoff;
- не допускать самовольного расширения scope.

### 2.2 `service-factory-codex-implementer`

Назначение: стандарт исполнения Git-visible задачи Codex.

Требования:
- отдельная ветка;
- exact base commit;
- не принимать продуктовые решения;
- tests + handoff;
- Draft PR;
- не merge собственный PR;
- не выполнять live write без отдельного owner gate.

### 2.3 `opiu-light-ux-guard`

Назначение: не дать новому сервису повторить тяжёлый технический UX OPIU.

Проверяет:
- normal UI использует бизнес-понятия;
- SHA/hashes/internal paths/proof JSON/debug codes не являются обязательным UX;
- пользователь видит простые статусы и понятные способы исправления;
- recovery/reselect/reset являются простыми действиями без скрытых side effects;
- не появляются лишние многоходовые блокировки.

### 2.4 `excel-transform-contract`

Назначение: контракт входного Excel и детерминированной трансформации.

Проверяет:
- источник определяется по структуре/schema, не по filename;
- formula cells читаются по рассчитанным значениям в рамках принятого Product Contract;
- трансформация отделена от UI/ADO;
- zero months и другие принятые бизнес-инварианты сохраняются;
- ошибки локализуются до ячейки/строки и попадают в Реестр ошибок;
- есть fixtures для реальных пограничных случаев.

### 2.5 `ado-1c-integration-safety`

Назначение: отдельный high-risk skill для будущего этапа ADO/1C.

Обязательные правила:
- сначала ADO read-only / DRY_RUN;
- exact target identity;
- immutable load plan;
- idempotency key;
- explicit TEST/PROD owner authority;
- transaction/rollback where feasible;
- post-load read-back verification;
- `Execute success` не равен успешной загрузке;
- direct SQL writes во внутренние таблицы 1С требуют отдельного архитектурного решения и не выбираются Codex молча.

### 2.6 `support-bundle-triage`

Назначение: диагностировать проблемы без технического перегруза пользователя.

Должен собирать sanitized support bundle:
- RUN metadata;
- версии;
- business-safe error registry;
- relevant logs;
- source/target fingerprints where allowed;
- без паролей, connection strings, токенов и иных секретов.

### 2.7 `deterministic-release-gate`

Назначение: исключить выпуск устаревшей сборки.

Проверяет:
- release source commit = текущий accepted product head;
- package создан из exact head;
- clean-room package launch;
- package boundary tests;
- release не использует `latest file`/случайный артефакт;
- release candidate не равен разрешению production/live 1C.

## 3. Плагины / подключения / инструменты

### Обязательная основа

- **GitHub connection/plugin** — репозиторий, Issues, branches, PR, commits, diffs, releases, GitHub Actions. Это основной мост между координатором и Codex.
- **Codex** — исполнитель точных Git-visible задач, не источник продуктовых решений.
- **ChatGPT Project** — coordinator/Product/UX workspace с Project-only memory.
- **AGENTS.md** — постоянные правила для Codex внутри репозитория.

### Добавлять по мере необходимости, не заранее

- **Google Drive connection** — только если реальные Excel/справочники будут регулярно храниться в Drive и это уменьшит ручную передачу файлов. Не является обязательным для первой vertical slice.
- Другие подключения добавляются только под доказанную задачу. Не подключать Jira/Linear/Airtable и отдельные task trackers просто ради процесса: GitHub Issues/PR достаточно, пока не доказано обратное.

### Инструменты разработки

- **Playwright** — подключить с первой UI vertical slice; e2e должен проверять happy path и recovery/error scenarios.
- **Excel library** — выбрать после фиксации языка/runtime реализации; библиотека должна уметь читать workbook structure, formulas + cached values и ячеечные ошибки без обязательного запуска desktop Excel.
- **Unit/integration/e2e tests** — с первой vertical slice.
- **Secret/leak scanning** — до подключения реальных ADO credentials.
- **Security review** — обязательна перед live ADO/write.
- **Support bundle** — после появления реального runtime и пользовательской диагностики.

## 4. Очерёдность внедрения Skills и инструментов

Не создавать все Skills в первый день. Последовательность:

1. Product Contract + User Flow — без Codex implementation.
2. Первая vertical slice `Excel → validation → transformation → preview`.
3. После стабилизации первого slice оформить reusable `excel-transform-contract` и `opiu-light-ux-guard` на основе реально проверенных правил, а не абстракций.
4. Оформить `service-factory-coordinator` и `service-factory-codex-implementer`, когда будет первый полный цикл Issue/Task → Codex → PR → review.
5. Перед ADO DRY_RUN оформить `ado-1c-integration-safety`.
6. После появления runtime/support cases — `support-bundle-triage`.
7. Перед первым настоящим release — `deterministic-release-gate`.

То есть Skills извлекаются из работающего процесса; не строить большую мета-систему раньше продукта.

## 5. Модель риска и reasoning/model routing

### ChatGPT coordinator

- `FAST` — рутинные статусы, Git reading, простые governance updates.
- `STANDARD` — Product/User Flow, обычный Excel contract, vertical slice, обычный PR review.
- `HIGH` — архитектура, сложные трансформации, иерархии, context/idempotency, ADO, release/regression conflicts.
- `CRITICAL` — production DB write, migration, destructive operations, data-integrity decisions, финальный production gate.

### Codex

- **Luna** — механические/документальные/простые изменения.
- **Terra** — default implementation.
- **Sol** — критические изменения ADO/write/transactions/idempotency/refactor/migration/security.

Принцип: `S risk → FAST/STANDARD + Luna/Terra`; `M risk → STANDARD/HIGH + Terra`; `L risk → HIGH/CRITICAL + Sol`.

## 6. Архитектурные паттерны, которые Skills должны сохранять

- immutable RUN-local source snapshot;
- single-flight/idempotent business action;
- structural source detection, not filename heuristic;
- public DTO allowlists;
- business language public / technical internal;
- reselect/reset as first-class recovery action with zero write side effects;
- semantic readiness states;
- exact handoff between stages, never `latest file`;
- supersede artifacts, preserve history;
- Release Freshness Gate;
- clean-room package launch;
- browser E2E includes recovery/missing/ambiguous/drift/double-click/replay/restart;
- reuse patterns, not entire OPIU implementation.

## 7. Future ADO/1C target flow

Рекомендуемая безопасная форма:

`Excel → Transform → Validated staging → ADO → controlled receiver → 1C`

Не делать неявный переход к прямой записи во внутренние SQL-таблицы 1С. Если именно прямой SQL будет нужен, это отдельное high-risk architecture/owner decision.

Стадии будущей загрузки:

`INPUT_SELECTED → VALIDATING → INPUT_READY → TRANSFORMING → PREVIEW_READY → DRY_RUN → LOAD_PLAN_READY → WAIT_OWNER_LIVE_GATE → WRITING → VERIFYING → COMPLETED_VERIFIED`

До `WRITING` должны быть зафиксированы exact target identity, load plan, idempotency и authority. `WRITE_SUCCESS` не является финальным состоянием без read-back verification.

## 8. Что НЕ делать

- не переносить R005/R001/Rules Engine в новый сервис;
- не создавать source-proof UI с ручными SHA/hashes;
- не строить тяжёлую governance-машину до появления реальной необходимости;
- не внедрять семь Skills одновременно до первой работающей vertical slice;
- не подключать внешние task trackers без доказанной пользы;
- не разрешать Codex самостоятельно выбирать архитектуру live-write или merge PR;
- не считать build/ZIP/PASS разрешением на 1С.

## 9. Coordinator next action

Продолжить текущий Product Contract с реальными справочниками. После принятия User Flow определить первую vertical slice и только затем подготовить первый Codex Task Contract.

Этот документ должен использоваться координатором как исходный план Skills/plugins/tooling и обновляться только при явном изменении продукта или после появления фактического опыта первой vertical slice.
