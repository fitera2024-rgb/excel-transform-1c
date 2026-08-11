# Feature Baseline

STATUS: `PRODUCT_BASELINE_DRAFT / OWNER_ACCEPTED_INVARIANTS / NO_RELEASE_APPROVAL`

Каждый принятый функциональный инвариант получает стабильный ID. Потеря функции без явного разрешения = regression.

| ID | Area | Baseline |
|---|---|---|
| INPUT-001 | Excel | Пользователь может выбрать входной Excel |
| INPUT-002 | Excel | Источник определяется по структуре/schema, не по имени файла |
| INPUT-003 | Excel | V1 использует уже подготовленный загрузочный диапазон и не реконструирует его из расчётных департаментских листов |
| INPUT-004 | Excel | Формулы в загрузочном диапазоне разрешены; сервис читает рассчитанные/сохранённые значения, Paste Values не требуется |
| VAL-001 | Validation | Проблемы данных показываются пользователю понятным бизнес-языком |
| ERR-001 | Validation | Локальная ошибка не блокирует весь файл; пропускается только минимально необходимый результат |
| ERR-002 | Validation | Ошибка общего поля не исключает автоматически все 12 месяцев исходной строки |
| ERR-003 | Validation | Реестр ошибок/внимания содержит точный указатель на исходный Excel и максимум доступного бизнес-контекста |
| TAX-001 | Validation | `?`, пустое и неоднозначный числовой `0` по налогообложению требуют внимания, но не блокируют весь preview |
| CONTEXT-001 | Context | Контекст выбирается пользователем из загруженных утверждённых справочников, не угадывается по filename/path/случайной ячейке |
| CONTEXT-002 | Context | `Единица отчёта` и `Организация пути 1С` не объединяются без доказанного mapping |
| CONTEXT-003 | Context | `Сценарий` и `Период сценария` являются отдельными полями |
| MAP-001 | ERP mapping | ERP-код выбирается автоматически только при точном однозначном match по принятой иерархии/атрибутам |
| MAP-002 | ERP mapping | При неоднозначности пользователь выбирает ERP-код вручную; autonomous fuzzy/typo auto-match запрещён |
| TRANS-001 | Core | Трансформация отделена от UI и ADO |
| TRANS-002 | Core | Каждая исходная загрузочная строка нормализуется во все 12 месяцев, включая нулевые значения |
| PREVIEW-001 | UI | Результат можно проверить до live write |
| PREVIEW-002 | UI | Неполные записи остаются в основном preview со статусом `Требует внимания`; скрытый карантин не создаётся |
| UX-001 | UI | Normal UI использует бизнес-понятия, technical details скрыты |
| UX-002 | UI | Reselect/reset не создаёт RUN и не пишет данные |
| UX-003 | UI | Пользователь может исправлять бизнес-реквизиты в сервисе из загруженных справочников; исходное значение не подменяется тихо |
| RESULT-001 | Output | Пользовательский result — упрощённый business format; технический 34-column sample не является обязательным target format |
| RUN-001 | Audit | Каждый processing run имеет RUN-ID |
| RUN-002 | Audit | RUN использует immutable snapshot exact input |
| RUN-003 | Audit | Один бизнес-запуск single-flight/idempotent |
| ADO-001 | Adapter | До отдельного owner gate ADO работает только read-only/DRY RUN |
| WRITE-001 | Safety | Live write по умолчанию запрещён |
| WRITE-002 | Safety | Успех write требует post-load/read-back verification |
| REL-001 | Release | Release source соответствует текущему принятому product head |
| GOV-001 | Governance | Codex не merge-ит PR самостоятельно |
| GOV-002 | Governance | Реализацию первой vertical slice не начинать до принятия владельцем User Flow |

## Result values

`PRESERVED / CHANGED_AUTHORIZED / REMOVED_AUTHORIZED / BLOCKED_REGRESSION`.
