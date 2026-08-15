# Coordinator QA — автоматическое соответствие статей и показателей

STATUS: `BLOCKED_BY_CODEX / NO_MERGE / NO_LIVE_WRITE`

## Authority

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Working branch: `feat/final-owner-smoke-fitera-v2`.
- Registry: `governance/tasks/WORK-REGISTRY-AUTO-ARTICLE-INDICATOR-20260815-001.md`.
- Codex task: `governance/tasks/CODEX-TASK-AUTO-ARTICLE-INDICATOR-20260815-001.md`.
- Expected Codex marker: `READY_FOR_COORDINATOR_QA_AUTO_INDICATORS`.

## Coordinator responsibilities

1. Проверить точный base/head, ветку и Draft PR.
2. Прочитать diff, handoff и все новые тесты.
3. Убедиться, что normal user не управляет техническим Rules workflow.
4. Проверить, что auto-match применяет только уникальное точное соответствие.
5. Проверить отсутствие fuzzy, typo, case-only и contains matching.
6. Проверить, что листы идут строго:
   - `OPIU Light`;
   - `ОПИУ`;
   - `Показатели`.
7. Проверить неизменность старой схемы `OPIU Light`.
8. Проверить точные 17 колонок `ОПИУ` и 8 колонок `Показатели`.
9. Проверить агрегирование одинакового ключа показателя.
10. Проверить нули, отрицательные суммы и месячные ошибки.
11. Проверить, что отсутствующие коды остаются пустыми, но строки не удаляются.
12. Проверить повторный автопоиск после дополнения классификатора без повторного чтения исходного Excel.
13. Прогнать пример ADO и synthetic ambiguous/missing cases.
14. Проверить Windows offline package, launcher, restart, STOP_SERVICE и ZIP integrity.
15. Вернуть только один результат:
   - `CHANGES_REQUIRED_AUTO_INDICATORS`;
   - `READY_FOR_OWNER_SMOKE_AUTO_INDICATORS`.

## Owner smoke

Owner smoke должен подтвердить:

- пользователь не открывает и не редактирует правила;
- сервис сам находит прямые соответствия;
- на экране понятны counts найденных и нерешённых;
- `Показатели` реально заполнен, когда классификатор содержит соответствия;
- нерешённые строки не исчезают;
- старый `OPIU Light` остаётся доступным;
- export открывается как корректный XLSX.

Merge разрешён только после явного `ПРИНИМАЮ` владельца.

`NO ADO / NO ODBC / NO 1C / NO LIVE WRITE / NO MERGE`.
