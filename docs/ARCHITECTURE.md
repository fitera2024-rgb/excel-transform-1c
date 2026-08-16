# Architecture Light

STATUS: `CANONICAL_PREVIEW_EXPORT_BOUNDARIES_ACCEPTED / L_INTEGRATION / NO_LIVE_WRITE`

```text
Local UI
  ↓
Application / Workflow
  ↓
Business Core
  ↓
Adapters
  ├─ Excel input/output
  ├─ OPIU formula / analytics / MXL sources
  ├─ ERP and business reference files
  ├─ Local persistence
  └─ ADO / 1C — later, not in preview/export scope
  ↓
Runs / Logs / Support
```

## V1 components

### Local UI

- выбор организационного контекста, сценария, года/месяцев и Excel;
- добавление локального сценария;
- загрузка/дополнение принятых business reference и OPIU source files;
- максимально полный preview полного БДР, подготовленных бюджетов и Инталев ОПИУ;
- Реестр ошибок/внимания и unresolved formula/source rows;
- явные пользовательские исправления;
- экспорт `OPIU Light / ОПИУ / Показатели`.

UI использует бизнес-понятия. SHA, internal paths, proof JSON, SQL IDs и технические blocker codes не являются обязательными пользовательскими элементами.

### Application / Workflow

Оркестрирует один пользовательский процесс:

`select context → select Excel → detect source family → read exact values → validate → resolve ERP/tax/CFO/indicator → normalize → preview → correct → three-sheet export`

Один business action не создаёт дублирующий RUN. Перевыбор и reset не выполняют write.

### Business Core

Содержит детерминированные правила:

- структурное обнаружение подготовленных бюджетов, полного БДР и annual/monthly Intalev OPIU;
- чтение сохранённых значений формул без пересчёта Excel;
- exact saved-value resolution для полного БДР;
- отдельную семантику KPI, доходов и расходов;
- разворот годовых строк во все 12 месяцев и сохранение доказанного месяца для monthly source;
- локализацию ошибок до минимальной единицы;
- exact ERP mapping и reusable mapping key;
- exact CFO/organization/channel context;
- exact indicator resolution с принятой precedence;
- статусы `ОК`, `Требует внимания`, `Пропущено`;
- правила налогообложения и отрицательных сумм;
- формирование business-safe row DTO и aggregate DTO.

Business Core не зависит от UI, ADO connection objects и абсолютных filesystem paths.

### Excel adapter

- определяет фактический контейнер по bytes/internal parts, не по filename suffix;
- сохраняет immutable original snapshot и подготавливает отдельную working copy;
- локально расшифровывает поддерживаемый encrypted OOXML, конвертирует legacy BIFF/SpreadsheetML и консервативно ремонтирует однозначный OOXML;
- определяет business source по структуре/schema, не по имени листа;
- поддерживает подготовленные expense/revenue ranges, полный БДР и отдельный structural parser annual/monthly Intalev OPIU;
- сохраняет точную связь между видимой Excel-строкой и отдельной RUN-local identity;
- читает formula cells по сохранённым calculated values и exact saved-value sheet;
- не является Excel Calculation Engine и не требует Excel COM;
- сохраняет точные source pointers: файл, лист, строка, ячейка, поле/месяц;
- экспортирует три листа `OPIU Light / ОПИУ / Показатели` с каноническими business headers.


### OPIU sources adapter

Структурно читает принятый комплект бизнес-источников для показателей ОПИУ:

- формулы;
- аналитики;
- справочник показателей ERP;
- MXL/source definitions;
- регионы;
- сети/каналы.

Adapter не выбирает показатель сам. Он формирует нормализованные exact source DTO для Business Core, сохраняет source identity и отклоняет неподдержанную/неоднозначную структуру без guessing.

### Indicator resolution inside Business Core

Применяется явная precedence:

1. KPI полного БДР сохраняет точный source indicator и не требует статьи расходов.
2. Доходы и количества используют принятые exact structural resolvers.
3. Для расходов при наличии formula/source catalog authority действует цепочка `группа раскрытия → статья → supported exact predicates → показатель`.
4. Legacy classifier допускается только как exact `группа → статья` fallback, когда formula/source authority отсутствует.
5. Неподдержанное или неоднозначное условие fail closed только для indicator resolution: row-level preview/export сохраняется, aggregate `Показатели` не заполняется догадкой.

`core/opiu_rules` — узкий доменный модуль для принятых источников. Он не является универсальным Rules Engine, plugin framework или normal-user rules editor.

### Reference adapter

Загружает packaged baseline catalogs при первом старте и структурно читает пользовательские дополнения в документированных форматах ERP без ручной перестройки в промежуточный шаблон. Merge выполняется только по exact stable identity:

- ERP-статьи;
- организационное дерево;
- сценарии;
- ЦФО Инталев;
- показатели, регионы, сети и другие принятые справочники.

Не придумывает активность, тип узла или связи, которых нет в данных/контракте.
Тесты используют только вымышленные книги, повторяющие структуру этих выгрузок.

### Local persistence adapter

Минимально хранит:

- пользовательские сценарии и стабильные local IDs;
- ERP-код как необязательный атрибут сценария;
- подтверждённые ручные ERP mappings по принятому reusable key;
- exact source-CFO mappings;
- нормализованные OPIU formula/source rules и их source identity;
- необходимые user overrides текущего результата.

Отдельная делегация пользователей удалена из локального V1 по owner decision; всё загруженное дерево доступно normal user.

Это локальное хранилище одного внутреннего сервиса, не multi-tenant platform database.

### Runs / Logs / Support

- каждый processing run имеет RUN-ID;
- после выбора входа используется exact RUN-local snapshot;
- downstream получает exact handoff, а не ищет `latest file`;
- журнал и support information не содержат паролей, токенов и connection strings.

## Safety boundary V1

Для preview действует `continue with attention`.

Полная остановка только если:

- файл невозможно открыть/он повреждён;
- не найден ни один распознаваемый загрузочный диапазон;
- технически невозможно получить полезный результат.

V1 не содержит ADO, live write, TEST/PROD write или прямого SQL-write.

## Delivery stages

1. **Canonical preview/export candidate:** prepared budgets + full BDR + annual/monthly Intalev → exact business resolution → maximum preview → three-sheet export.
2. Independent coordinator QA, source reconciliation and Owner UX Smoke on one exact package.
3. Merge/release — отдельный явный gate после smoke.
4. ADO read-only / DRY RUN — отдельный будущий контракт.
5. TEST write — только после отдельного owner gate.
6. Production write — отдельный owner gate.

## Implementation freedom

Конкретный язык, framework и UI toolkit выбираются в implementation task по принципу самого простого поддерживаемого решения, которое:

- сохраняет эти слои и тестируемость Business Core;
- устойчиво читает реальные Excel и cached formula values;
- поддерживает локальное постоянное хранилище;
- не создаёт platform/enterprise architecture.

## V1 implementation stack

Реализация использует предпочтительный baseline Task Contract без изменения
принятой архитектуры:

- Python 3.11+;
- FastAPI + server-rendered Jinja templates;
- SQLite для локальных сценариев, справочников, exact mappings, OPIU rules и overrides;
- openpyxl для structural detection, чтения cached formula values и OPIU Light export;
- pytest/TestClient для unit, integration и UI smoke.

Это один локальный процесс без SPA, очередей, multi-tenant слоя, универсального Rules Engine, ADO connection
objects или write adapters. Загруженный файл копируется в immutable RUN-local
snapshot до чтения; один и тот же exact input/context/candidate в текущем
процессе возвращает существующий RUN вместо создания дубликата.
