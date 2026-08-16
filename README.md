# excel-transform-1c

Лёгкий внутренний сервис для цепочки:

`Excel → validation → transformation → preview → later ADO DRY RUN → controlled 1C write`.

## Практическое назначение

Сервис создаётся как **локальная внутренняя утилита для повторяемого преобразования ограниченного набора бюджетных Excel-таблиц в согласованный формат для 1С**.

Это не универсальная интеграционная платформа, не multi-tenant SaaS и не глобальный сервис. Основной результат — корректно преобразованные данные, понятный preview и файл/набор данных в формате, пригодном для дальнейшей загрузки в 1С.

ADO и фактическая запись в 1С являются отдельным последующим этапом и не должны усложнять первую версию конвертера.

## Current status

`OWNER GATE ACCEPTED / PR #24 + PR #25 CANONICAL L INTEGRATION / DRAFT / NO MERGE / NO LIVE WRITE`

Владелец `2026-08-17` принял единый canonical preview/export scope: подготовленные бюджеты, полный БДР с KPI/доходами/расходами, annual/monthly Intalev OPIU, exact formula/source indicator resolution и три листа `OPIU Light / ОПИУ / Показатели`.

Каноническая работа ведётся в Issue #27 и Draft PR #28. Исходные PR #24 и PR #25 отдельно не merge-ятся. ADO, ODBC, SQL/1C write и live write отсутствуют и не разрешены.

## Start here

1. `governance/handoffs/HANDOFF-OWNER-GATE-CANONICAL-PREVIEW-EXPORT-20260817-001.md` — owner gate на объединение PR #24 + PR #25.
2. `governance/tasks/CODEX-TASK-CANONICAL-PREVIEW-EXPORT-INTEGRATION-20260817-001.md` — exact L-level integration contract.
3. `governance/handoffs/HANDOFF-OWNER-DECISIONS-20260812-002.md` — исходные owner decisions и User Flow.
4. `governance/handoffs/HANDOFF-EXCEL-LOGIC-20260812-001.md` — карта реальных Excel, ERP-справочников и доказательств.
5. `docs/PRODUCT.md`
6. `docs/USER_FLOW.md`
7. `governance/DECISIONS.md`
8. `governance/FEATURE_BASELINE.md`
9. `governance/ACTIVE_WORK.md`
10. `docs/ARCHITECTURE.md`
11. `AGENTS.md` — правила для Codex
12. `docs/SERVICE_FACTORY_SKILLS_AND_PLUGINS_PLAN_RU.md` — справочный план reusable Skills и tooling; не является разрешением раздувать scope.

## Product principle

Новый сервис — быстрый рабочий помощник: максимум корректных данных сохраняется в preview, локальные проблемы показываются в Реестре ошибок/внимания и не должны превращаться в тяжёлые многоходовые блокировки.

## Принцип соразмерности

Не строить безопасность, governance и архитектурные слои ради самих слоёв. Для локального конвертера применяются только меры, которые прямо защищают корректность преобразования, исходные данные, повторяемость результата или будущую фактическую запись в 1С.

Любой новый контроль должен быть связан с конкретным реальным риском и не иметь более простого решения. Иначе он откладывается или не входит в scope.

## Boundary

OPIU используется только как visual/UX reference и источник отдельных проверенных reliability/safety patterns. Новый сервис не является fork OPIU.

Канонический preview/export candidate не пишет в 1С/БД. Live write по умолчанию запрещён и требует отдельного будущего owner gate.

## Локальный запуск V1

Требуется Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m excel_transform_1c.main
```

Откройте `http://127.0.0.1:8000`. Runtime-данные, загруженные файлы, локальная
SQLite-база и RUN-local snapshots создаются в `runtime/` и исключены из Git.

V1 напрямую принимает документированные выгрузки ERP `.xlsx` из текущего
Product Contract:

- иерархию `Статьи доходов и расходов`, где кодированная статья связывается с
  точным путём `тип → группа → статья`;
- единое иерархическое дерево `Организации` с кодом, родителем и полным путём;
- `Сценарии`, включая выгрузки без отдельной колонки года (год извлекается
  только из однозначного имени; иначе пользователь задаёт его при запуске).

Ручное преобразование этих ERP-выгрузок в промежуточный шаблон не требуется.
Для синтетических интеграций также поддерживаются плоские interchange-схемы:

- ERP-статьи: `Код`, `Официальное наименование`, `Тип расходов`, `Группа расходов`, `Исходная статья`;
- организации: `ID`, `Код`, `Наименование`, `Родитель ID`, `Полный путь`;
- сценарии (необязательно): `Наименование`, `Год`, `ERP-код`, `Комментарий`.

Бюджетный диапазон определяется структурно по восьми бизнес-колонкам и всем
12 месяцам, а не по имени листа. Формулы читаются через сохранённые calculated
values; приложение не пересчитывает Excel.

После чистого запуска уже доступны packaged baselines: `271` ERP-статья, `357` организаций/узлов, `12` сценариев и `16` ЦФО Инталев. Пользовательский `Загрузить / дополнить` сохраняет baseline и объединяет данные только по exact stable identity.

Фактический Excel-контейнер определяется по содержимому. Поддерживаются обычный OOXML, encrypted OOXML, legacy BIFF/XLS, SpreadsheetML XML и узко восстанавливаемый OOXML. Оригинал сохраняется неизменным; обработка использует отдельную working copy и не требует Excel COM.

Поддерживаются три structural families:

- подготовленные budget ranges расходов и доходов;
- полный БДР как один RUN с KPI, доходами, расходами и exact saved values;
- годовой и одногомесячный Инталев ОПИУ.

Для расходов indicator определяется только по exact цепочке `группа раскрытия → статья → supported formula/source predicates → показатель`. KPI не требует expense article. Legacy classifier допускается только как exact fallback при отсутствии formula/source authority. Global name-only, fuzzy, contains, typo/case correction запрещены.

Пользовательский XLSX содержит `OPIU Light`, `ОПИУ` и `Показатели`; отсутствие indicator не удаляет row-level сумму и не создаёт guessed aggregate.

Excel-ошибка конкретного месяца остаётся видимой в основном preview и экспорте
как `Пропущено`: сумма пуста, причина и точный адрес ячейки находятся в Реестре
ошибок. Остальные 11 месяцев строки продолжают обрабатываться.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit -q
.\.venv\Scripts\python.exe -m pytest tests/integration -q
.\.venv\Scripts\python.exe -m pytest tests/ui -q
```

Тестовые workbook/reference данные полностью синтетические и генерируются во
временных каталогах; реальные бизнес-Excel в репозитории отсутствуют.
