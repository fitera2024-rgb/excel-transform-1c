# Handoff — автоматическое соответствие статей и показателей

- Status: `READY_FOR_COORDINATOR_QA_AUTO_INDICATORS`.
- Repository: `fitera2024-rgb/excel-transform-1c`.
- Working branch: `feat/final-owner-smoke-fitera-v2`.
- Draft PR: `#23`, остаётся Draft.
- Exact task base: `f6b59a358a36dc517a1a1d8fb24003baf751c04c`.
- Exact tested implementation/package head: `587f6e371315884c340736016ba88c76c57a27f1`.
- GitHub Actions run: `31856037757`, `SUCCESS`.
- Safety: `NO ADO / NO ODBC / NO 1C / NO LIVE WRITE / NO MERGE`.

Exact final delivery head, содержащий этот handoff, фиксируется в Draft PR после публикации. После tested implementation head добавляется только этот governance-документ; поведение приложения и пакетный source не меняются.

## Реализованное поведение

- Классификатор `статья → показатель` структурно читается из локального Excel и сохраняется в `runtime/local.db`.
- Импорт `Загрузить / дополнить` добавляет правило либо обновляет только тот же exact stable key; порядок строк и имя файла не являются authority.
- Business Core проверяет ключи строго по приоритету:
  1. точный ERP-код статьи;
  2. точный полный путь `Тип расходов → Группа расходов → Статья`;
  3. точное имя статьи только при единственном кандидате во всём загруженном классификаторе.
- Допустима только обратимая техническая операция `trim`; регистр и текст сохраняются.
- При `0` кандидатах результат имеет состояние `missing`; при `>1` — `ambiguous`; неполное правило без показателя либо канала — `incomplete`.
- Ни одно из этих состояний не подставляет первый, похожий или исправленный вариант.
- Повторный импорт классификатора применяет matcher к уже существующим `PreviewRecord` текущего RUN. `read_path` и повторное чтение исходного Excel не вызываются; `rerun_count` остаётся `0`.
- Результат indicator matching хранится отдельно от legacy preview status/reasons. Поэтому первые два экспортных листа не меняются.

## Схема классификатора

Обязательные выходные колонки диапазона:

- `Показатель`;
- `Канал сбыта`.

Нужен хотя бы один явный exact key:

- `ERP-код статьи` (aliases: `Код ERP-статьи`, `Код статьи`);
- `Полный путь статьи` (alias: `Полный бизнес-путь статьи`);
- `Статья` (aliases: `Исходная статья`, `Наименование статьи`).

Полный путь также можно задать тремя колонками `Тип расходов`, `Группа расходов`, `Статья`; в persistence сохраняется точная строка с разделителем ` → `.

Persisted DTO:

- `erp_code`;
- `article_path`;
- `article_name`;
- `indicator`;
- `sales_channel`.

Stable merge identity использует первый заполненный ключ в том же порядке `erp_code → article_path → article_name`. Пустой показатель или канал сохраняется как неполное прямое правило, но не создаёт строку экспорта.

## UI

В preview добавлен один business-блок без Rules workflow:

- `Найдено автоматически: N` — число source rows с одним complete exact match;
- `Требует внимания: N` — все unresolved source rows (`missing`, `ambiguous`, `incomplete`);
- `Не найдено: N` — подмножество unresolved без кандидата;
- `Классификатор: загружен / не загружен`;
- действие `Загрузить / дополнить классификатор` и повторить поиск в текущем RUN.

Счётчики считаются по исходным строкам, а не по двенадцати месячным записям. Technical Rules UI, fuzzy suggestions, candidate ordering и internal keys пользователю не показываются. Остаток разрешается дополнением business-классификатора.

## Экспорт

Порядок листов строго сохранён:

1. `OPIU Light` — прежние 19 колонок и прежние строки;
2. `ОПИУ` — прежние 17 колонок и прежние строки;
3. `Показатели` — 8 колонок:
   `Организация`, `Сценарий`, `Год`, `Месяц`, `Период`, `Канал сбыта`, `Тип расходов`, `Сумма`.

На лист `Показатели` попадают только complete exact matches. Результаты детерминированно агрегируются по всем семи измерениям выходного ключа, сумма является восьмой колонкой. Нулевые и отрицательные значения сохраняются. Месячная ошибка с `amount=None`, отсутствующий показатель или канал строку не создают. Пустые дополнительные ERP/организационные коды по-прежнему не удаляют строки первых двух листов и не блокируют экспорт.

Integration test сравнивает все значения `OPIU Light` и `ОПИУ` до и после загрузки классификатора; оба листа идентичны.

## Изменённые файлы

Business Core и модели:

- `src/excel_transform_1c/core/indicator_matching.py`;
- `src/excel_transform_1c/core/models.py`.

Adapters / workflow / UI:

- `src/excel_transform_1c/adapters/references.py`;
- `src/excel_transform_1c/adapters/excel.py`;
- `src/excel_transform_1c/application/service.py`;
- `src/excel_transform_1c/ui/app.py`;
- `src/excel_transform_1c/ui/templates/run.html`.

Package and CI:

- `packaging/user/README_USER_RU.md`;
- `.github/workflows/final-owner-smoke-package-v2.yml`.

Tests:

- `tests/unit/test_article_indicator_matching.py`;
- `tests/integration/test_article_indicator_workflow.py`;
- `tests/ui/test_ui_smoke.py`;
- `tests/helpers/workbooks.py`.

Handoff:

- `governance/handoffs/HANDOFF-AUTO-ARTICLE-INDICATOR-20260815-001.md`.

Legacy/protected intake, ERP hierarchy parser, CFO matching semantics, launcher/port cleanup и ADO/live-write adapters не изменялись.

## Test evidence

Добавлено `14` CODEX-01 acceptance tests:

- exact ERP code;
- exact full path fallback;
- unique exact name;
- ambiguity independent of row order;
- missing candidate;
- case mismatch;
- typo and contains mismatch;
- incomplete channel/indicator;
- deterministic aggregation;
- zero, negative and monthly error behavior;
- classifier parsing and persistence after restart;
- current-RUN refresh without `read_path`;
- unchanged `OPIU Light` / `ОПИУ` and populated `Показатели`;
- compact UI without Rules workflow.

Local synthetic verification:

- compileall: PASS;
- unit: `43 passed`;
- integration: `45 passed, 5 skipped`;
- UI: `29 passed`;
- full regression: `117 passed, 5 skipped`, one external Starlette/TestClient deprecation warning;
- skipped tests require optional real owner-evidence files; no real Excel was read;
- JavaScript syntax and `git diff --check`: PASS.

Local Windows worktree package verification:

- application wheel and complete x64 offline wheelhouse: PASS;
- offline install into fresh package `.venv`: PASS;
- synthetic input → classifier → 12 indicator rows: PASS;
- exact three-sheet order and unchanged first two row counts: PASS;
- ZIP integrity: PASS.

An already running owner service on local port `8000` was deliberately not stopped. Exact launcher/restart/STOP smoke was instead performed in the isolated Windows CI job below.

## CI and Windows package

GitHub Actions run `31856037757` completed successfully on exact tested head `587f6e371315884c340736016ba88c76c57a27f1`.

Ubuntu job:

- compileall, unit, integration, UI and full regression: PASS;
- wheel resource check, including `core/indicator_matching.py`: PASS;
- tracked business Excel: `0`.

Isolated Windows job:

- offline wheelhouse and user ZIP build: PASS;
- `START_SERVICE` and `/health`/home markers: PASS;
- baseline counts `271 / 357 / 12 / 16`: PASS;
- synthetic classifier count `1 / 0 / 0`: PASS;
- `Показатели` contains 12 monthly rows, including zero months: PASS;
- second start replaces the first PID: PASS;
- `STOP_SERVICE` releases the service: PASS;
- ZIP integrity and checksum: PASS.

Artifact:

- name: `EXCEL_TO_OPIU_LIGHT_FITERA_FINAL_WINDOWS_V2`;
- artifact id: `9239098386`;
- inner ZIP: `EXCEL_TO_OPIU_LIGHT_USER_587f6e371315.zip`;
- inner ZIP SHA-256: `4badb7e26b1965a7abbab2e96f983baa323d19cc1b96d1a8539af1a7787b902f`;
- GitHub artifact digest: `sha256:8dc8e3da278660bb21e384e309fe4079c8b7249ecda30b267c6e28d3cb9361eb`;
- retention through `2026-08-29`.

## Feature Baseline result

- `PRESERVED`: structural input detection, immutable RUN snapshot, single-flight RUN, ERP/tax/CFO corrections, protected/legacy intake, continue-with-attention, old `OPIU Light`, `ОПИУ`, no live write.
- `CHANGED_AUTHORIZED`: local direct classifier, exact article-indicator matching, compact counts, populated `Показатели`, current-RUN rematch.
- `REMOVED_AUTHORIZED`: none in CODEX-01.
- `BLOCKED_REGRESSION`: none.

## Ограничения и нерешённые вопросы

- Реальные owner Excel, ADO, ODBC, 1C, SQL и runtime databases не использовались и в Git не добавлялись.
- Классификатор обязан явно дать канал сбыта; сервис не выводит и не угадывает его из похожего текста.
- Точное имя является fallback только при уникальности во всём classifier. Если одна статья повторяется под разными code/path rules, name-only source остаётся неоднозначным.
- Текущий RUN хранится в памяти процесса; после restart исходный Excel нужно выбрать заново. Сам классификатор сохраняется в SQLite и применяется к новым RUN.
- В рамках принятого Task Contract дополнительных блокирующих вопросов нет.

Merge не выполнялся.

`READY_FOR_COORDINATOR_QA_AUTO_INDICATORS`
