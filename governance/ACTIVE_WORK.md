# Active Work

STATUS: `DISCOVERY / COORDINATOR_HANDOFF_READY`

## Current phase

Новый сервис находится на этапе Product Contract + User Flow.

Полный handoff текущего discovery:

`governance/handoffs/HANDOFF-COORDINATOR-20260811-001.md`

## Current owner gate

До реализации требуется:

- загрузить и изучить реальные справочники контекста/бизнес-реквизитов;
- уточнить оставшиеся Product Contract вопросы по одному;
- принять User Flow владельцем.

Исходный бюджетный Excel и ERP-справочник статей уже были исследованы на discovery-этапе; результаты анализа и принятые решения перенесены в handoff, `docs/PRODUCT.md`, `governance/DECISIONS.md` и `governance/FEATURE_BASELINE.md`.

## Forbidden now

- начинать production implementation до owner acceptance User Flow;
- подключать ADO write;
- писать в TEST/PROD 1С;
- делать прямой SQL-write во внутренние таблицы 1С без отдельного high-risk решения;
- переносить код/многоходовые блокировки OPIU целиком;
- создавать релиз до owner UX smoke;
- переоткрывать уже принятые продуктовые решения без нового evidence/owner decision.

## Next action

`LOAD_AND_ANALYZE_REFERENCE_DIRECTORIES`

Координатор нового сервиса должен получить реальные справочники и для каждого составить карту:

`справочник → ключ/код → наименование → иерархия → доказанные связи → количество записей`.

После анализа задать владельцу только один следующий самый важный Product Contract вопрос.

## Handoff boundary

Текущий OPIU-координатор после `HANDOFF-COORDINATOR-20260811-001` возвращается к работе над OPIU. Дальнейший discovery нового сервиса ведёт отдельный координатор через этот Git-репозиторий.
