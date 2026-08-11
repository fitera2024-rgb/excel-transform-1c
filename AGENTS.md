# AGENTS.md

## Роль Codex

Codex — исполнитель конкретной Git-visible задачи. Он не принимает продуктовые решения и не расширяет scope самостоятельно.

## Перед работой

1. Прочитать `docs/PRODUCT.md`, `docs/USER_FLOW.md`, `docs/ARCHITECTURE.md`.
2. Прочитать `governance/FEATURE_BASELINE.md`, `governance/ACTIVE_WORK.md` и связанную задачу/CR.
3. Зафиксировать base commit и работать в отдельной ветке.

## Обязательные правила

- Не merge PR самостоятельно.
- Не выполнять live-write в 1С/БД без отдельного owner gate.
- Не искать "latest file"; downstream использует exact handoff.
- Один бизнес-клик не должен создавать дублирующий RUN/write.
- Входы определяются по структуре/схеме, не по имени файла.
- Normal UI не показывает обязательные SHA, internal paths, proof JSON или technical blocker codes.
- Business Core не зависит от UI, ADO connection objects и filesystem paths.
- Для обработки использовать immutable RUN-local snapshot входов.

## Handoff после реализации

В PR/hand-off указать:
- что изменено;
- что сохранено;
- tests;
- риски/ограничения;
- Feature Baseline result;
- exact head.

PR создавать Draft. Owner/координатор принимает решение о merge отдельно.
