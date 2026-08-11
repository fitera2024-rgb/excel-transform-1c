# Feature Baseline

STATUS: `STARTER_BASELINE`

Каждый принятый функциональный инвариант получает стабильный ID. Потеря функции без явного разрешения = regression.

| ID | Area | Baseline |
|---|---|---|
| INPUT-001 | Excel | Пользователь может выбрать входной Excel |
| INPUT-002 | Excel | Источник определяется по структуре/schema, не по имени файла |
| VAL-001 | Validation | Ошибки данных показываются до трансформации/write |
| UX-001 | UI | Normal UI использует бизнес-понятия, technical details скрыты |
| UX-002 | UI | Reselect/reset не создаёт RUN и не пишет данные |
| RUN-001 | Audit | Каждый processing run имеет RUN-ID |
| RUN-002 | Audit | RUN использует immutable snapshot exact input |
| RUN-003 | Audit | Один бизнес-запуск single-flight/idempotent |
| TRANS-001 | Core | Трансформация отделена от UI и ADO |
| PREVIEW-001 | UI | Результат можно проверить до live write |
| ADO-001 | Adapter | До отдельного owner gate ADO работает только read-only/DRY RUN |
| WRITE-001 | Safety | Live write по умолчанию запрещён |
| WRITE-002 | Safety | Успех write требует post-load/read-back verification |
| REL-001 | Release | Release source соответствует текущему принятому product head |
| GOV-001 | Governance | Codex не merge-ит PR самостоятельно |

## Result values

`PRESERVED / CHANGED_AUTHORIZED / REMOVED_AUTHORIZED / BLOCKED_REGRESSION`.
