# Architecture Light

STATUS: `V1_BOUNDARIES_ACCEPTED / IMPLEMENTATION_ALLOWED / NO_LIVE_WRITE`

```text
Local UI
  ↓
Application / Workflow
  ↓
Business Core
  ↓
Adapters
  ├─ Excel input/output
  ├─ ERP reference files
  ├─ Local persistence
  └─ ADO / 1C — later, not in V1
  ↓
Runs / Logs / Support
```

## V1 components

### Local UI

- выбор организационного контекста, сценария, года/месяцев и Excel;
- добавление локального сценария;
- максимально полный preview;
- Реестр ошибок/внимания;
- явные пользовательские исправления;
- экспорт результата.

UI использует бизнес-понятия. SHA, internal paths, proof JSON, SQL IDs и технические blocker codes не являются обязательными пользовательскими элементами.

### Application / Workflow

Оркестрирует один пользовательский процесс:

`select context → select Excel → detect source → read → validate → map → normalize → preview → correct → export`

Один business action не создаёт дублирующий RUN. Перевыбор и reset не выполняют write.

### Business Core

Содержит детерминированные правила:

- структурное обнаружение подготовленного диапазона;
- чтение сохранённых значений формул без пересчёта Excel;
- разворот каждой исходной строки во все 12 месяцев;
- локализацию ошибок до минимальной единицы;
- exact ERP mapping;
- reusable mapping key;
- статусы `ОК`, `Требует внимания`, `Пропущено`;
- правила налогообложения и отрицательных сумм;
- формирование business-safe result DTO.

Business Core не зависит от UI, ADO connection objects и абсолютных filesystem paths.

### Excel adapter

- определяет фактический контейнер по bytes/internal parts, не по filename suffix;
- сохраняет immutable original snapshot и подготавливает отдельную working copy;
- локально расшифровывает поддерживаемый encrypted OOXML, конвертирует legacy BIFF/SpreadsheetML и консервативно ремонтирует однозначный OOXML;
- определяет business source по структуре/schema, не по имени листа;
- поддерживает подготовленный budget range и отдельный structural parser годового Инталев ОПИУ;
- читает formula cells по сохранённым calculated values;
- не является Excel Calculation Engine и не требует Excel COM;
- сохраняет точные source pointers: файл, лист, строка, ячейка, поле/месяц;
- экспортирует OPIU Light результат.

### Reference adapter

Загружает packaged baseline catalogs при первом старте и структурно читает пользовательские дополнения в документированных форматах ERP без ручной перестройки в промежуточный шаблон. Merge выполняется только по exact stable identity:

- ERP-статьи;
- организационное дерево;
- сценарии;
- другие принятые справочники.

Не придумывает активность, тип узла или связи, которых нет в данных/контракте.
Тесты используют только вымышленные книги, повторяющие структуру этих выгрузок.

### Local persistence adapter

Минимально хранит:

- пользовательские сценарии и стабильные local IDs;
- ERP-код как необязательный атрибут сценария;
- подтверждённые ручные ERP mappings по принятому reusable key;
- делегации узлов дерева;
- необходимые user overrides текущего результата.

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

1. **V1:** Excel → validation → exact mapping/manual correction → 12-month normalization → preview → export.
2. Validation/error UX stabilization and Owner UX Smoke.
3. ADO read-only / DRY RUN — отдельный контракт.
4. TEST write — только после отдельного owner gate.
5. Production write — отдельный owner gate.

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
- SQLite для локальных сценариев, справочников, делегаций, ручных mappings и overrides;
- openpyxl для structural detection, чтения cached formula values и OPIU Light export;
- pytest/TestClient для unit, integration и UI smoke.

Это один локальный процесс без SPA, очередей, multi-tenant слоя, ADO connection
objects или write adapters. Загруженный файл копируется в immutable RUN-local
snapshot до чтения; один и тот же exact input/context/candidate в текущем
процессе возвращает существующий RUN вместо создания дубликата.
