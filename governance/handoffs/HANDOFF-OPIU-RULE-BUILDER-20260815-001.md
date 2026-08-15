# Handoff — OPIU ERP Rule Builder

- Status: `READY_FOR_COORDINATOR_QA_OPIU_RULES`.
- Repository: `fitera2024-rgb/excel-transform-1c`.
- Branch: `feat/final-owner-smoke-fitera-v2`.
- Exact base: `ffcb887844638eaac7a059b58150bdc200bb7e34`.
- Exact repository HEAD used for tests: `ffcb887844638eaac7a059b58150bdc200bb7e34`.
- Delivery form: implementation remains in the local working tree; no commit, push or merge was performed.
- Safety: `NO ADO / NO ODBC / NO 1C / NO LIVE WRITE / NO MERGE`.

## Result

Добавлен Business Core `core/opiu_rules/` с моделью `OPIURule`, структурным
парсером, построителем каталога и строгим resolver. Главный ключ выбора — точная
группа раскрытия. Статья проверяется только внутри уже найденной группы;
name-only, fuzzy, contains, typo correction, case conversion и выбор первого
кандидата отсутствуют.

Алгоритм resolver:

1. exact группа раскрытия;
2. exact статья внутри группы;
3. обязательные аналитики и exact predicates формулы;
4. один кандидат → `AUTO_MATCH`;
5. ноль кандидатов → `NOT_FOUND`;
6. больше одного кандидата → `AMBIGUOUS`.

Причины normal UI используют только бизнес-язык: `Не найдена группа раскрытия`,
`Не найдена статья внутри группы раскрытия`, `Условия формулы не выполнены`,
`Найдено несколько показателей`. Формулы, SQL, rule IDs и технические ключи в UI
не выводятся.

## Разобранные exact sources

| Результат | Файл | SHA-256 | Извлечено |
|---|---|---|---:|
| `OPIU_FORMULA_RULES` | `ОПИУ ФОРМУЛЫ.xlsx` | `E8644766E8E46F9978F64EA88BB119A4A6125A00A3711B21942D035DA1F1D1CE` | 463 formula rules |
| `OPIU_ANALYTIC_RULES` | `ОПИУ аНАЛИТИКИ.xlsx` | `9B887E42EEDE2E37939A0B3E4AC10FD1F64F360A2724BE03CF0562FC6220DD35` | 517 analytic rows |
| `ERP_INDICATOR_CATALOG` | `ПоказателиОтчетов_ОПИУ_ЕРП.xlsx` | `914BF4EED2A636FB6EF5006BC688457A93577BD318625C239C8CF19B218E109B` | 682 catalog entries |
| `ERP_SOURCE_RULES` | `Источники для ОПИУ_ ЕРП.mxl` | `FA24195774E7E0D90F1AEE523EFCCF2EB4B51F9C02540251034C54A2258C7864` | 311 source rules |
| `REGION_CATALOG` | `Регионы.xlsx` | `6646190C5D77AF7FDD0C30BF4D79D273AC362DF95EB7DF3172C1E2C067D28C88` | 22 code+name entries |
| `NETWORK_CATALOG` | `СЕТИ.xlsx` | `4A5A498F9B3DAB6BBB20C897F64DAD5D1EBF120163BC4BF7C7B991C504932692` | 233 code+name entries |

Файлы прочитаны read-only с exact paths. Реальные XLSX/MXL и их копии в Git не
добавлялись.

## Метрики полного реестра

- Построено `38` OPIU rules.
- Из них `3` уже содержат exact leaf article из формульной иерархии.
- `35` являются group-scope templates; resolver не применяет их к произвольной
  статье. Workflow расширяет такие правила только по exact совпадению
  `ERPArticle.expense_type == disclosure_group`.
- Неоднозначностей ERP indicator catalog: `21`.
- Уникальных непокрытых group/article links без leaf-каталога: `28`.
- Всего записей `Unresolved`: `49` (`21` ambiguous + `28` missing leaf catalog).

Контрольный workbook `OPIU_RULE_COVERAGE_REPORT.xlsx` создан с листами:

- `Rules`: `38` строк;
- `Unresolved`: `49` строк;
- `Analytics`: `25` уникальных связей показатель/аналитики/источник.

SHA-256 workbook:
`A691CC3DB165F427202E1031A65B334E846062709302F0D7787A1EF639A38728`.

Workbook проверен через table inspection, общий scan Excel errors и визуальный
render каждого листа. Ошибки `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, `#N/A` не
найдены.

## Интеграция

- `WorkflowService.upload_opiu_rule_sources(...)` принимает шесть immutable byte
  payloads, строит и сохраняет внутренний `opiu_rules` catalog в SQLite.
- При restart правила восстанавливаются из persistence.
- Перед заполнением `Показатели` group-scope templates раскрываются только по
  точной ERP hierarchy текущего каталога статей.
- `PreviewRecord` дополнен business analytics `region`, `network`,
  `nomenclature`; существующий export использует region/nomenclature без
  выдумывания кодов.
- Старый upload классификатора сохранён как compatibility intake, но в OPIU
  resolver допускаются только записи с полным путём, из которого однозначно
  получены группа и статья. ERP-code-only и article-name-only больше не обходят
  группу раскрытия.
- Лист `Показатели` по-прежнему создаётся только для полностью сопоставленных
  строк с доказанным каналом; нули и отрицательные суммы сохраняются.
- UI показывает counts и дедуплированные бизнес-причины; internal rules не
  раскрываются.

## Changed files

Business Core:

- `src/excel_transform_1c/core/opiu_rules/__init__.py`;
- `src/excel_transform_1c/core/opiu_rules/opiu_formula_parser.py`;
- `src/excel_transform_1c/core/opiu_rules/opiu_rule_builder.py`;
- `src/excel_transform_1c/core/opiu_rules/opiu_indicator_resolver.py`;
- `src/excel_transform_1c/core/opiu_rules/opiu_rule_models.py`;
- `src/excel_transform_1c/core/models.py`;
- `src/excel_transform_1c/core/indicator_matching.py`.

Adapters/workflow/UI:

- `src/excel_transform_1c/adapters/opiu_sources.py`;
- `src/excel_transform_1c/adapters/persistence.py`;
- `src/excel_transform_1c/adapters/excel.py`;
- `src/excel_transform_1c/application/service.py`;
- `src/excel_transform_1c/ui/app.py`;
- `src/excel_transform_1c/ui/templates/run.html`.

Tests:

- `tests/unit/test_opiu_rule_resolver.py`;
- `tests/integration/test_opiu_rule_catalog.py`;
- `tests/integration/test_article_indicator_workflow.py`.

## Test evidence

- Targeted OPIU unit/integration: `13 passed`.
- Targeted legacy/UI regression: `2 passed`.
- Full suite with exact real annual OPIU evidence path:
  `132 passed, 3 skipped, 1 warning` in `56.92s`.
- `python -m compileall -q src`: PASS.
- `git diff --check`: PASS (only existing Windows LF/CRLF notices).
- Warning: external Starlette/TestClient deprecation; unrelated to this task.

Acceptance scenarios covered:

- one group + article → one indicator;
- same article in different groups → different indicators;
- missing group → attention;
- multiple rules → ambiguous;
- formula predicate changes selection;
- region changes selection;
- network changes selection;
- case and contains differences are not corrected;
- conflicting exact article code is not ignored;
- XLSX formulas + analytics + ERP indicator catalog + MXL are joined
  structurally and persisted across restart.

## Feature Baseline

- `PRESERVED`: immutable RUN input, structural Excel detection, ERP/CFO/tax
  behavior, three-sheet export, continue-with-attention, no live write.
- `CHANGED_AUTHORIZED`: indicator selection now requires disclosure group before
  article; formulas, ERP sources and analytics participate in rule construction.
- `REMOVED_AUTHORIZED`: name-only and ERP-code-only indicator fallback from the
  active Workflow resolver.
- `BLOCKED_REGRESSION`: none.

## Ограничения

- Provided formula/MXL authorities identify many disclosure groups but do not
  enumerate all leaf articles inside those groups. The implementation records
  this as unresolved and never treats a blank article as a wildcard.
- Exact expansion requires the current ERP article catalog to use the same exact
  disclosure-group text. Case changes, suffix removal and typo correction are
  intentionally absent.
- Region/network/nomenclature affect resolution only when present in the input
  record or an exact formula predicate; the current prepared-budget parser does
  not invent missing analytics.
- CI/PR/package publication was not requested and was not performed.
- ADO, ODBC, SQL, 1C and any live write were not called or added.

Merge не выполнялся.

`READY_FOR_COORDINATOR_QA_OPIU_RULES`
