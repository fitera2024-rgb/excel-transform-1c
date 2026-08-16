# HANDOFF BUGFIX-05B: ERP hierarchy reader и reference resolver

HANDOFF-ID: `HANDOFF-BUGFIX-05B-ERP-HIERARCHY-READER-20260816-001`

TASKS:

- `TASK-05B-01` / `BUGFIX-05B-01-ERP-HIERARCHY-READER-20260816-001`;
- `TASK-05B-02` / `BUGFIX-05B-02-ERP-CODE-RESOLUTION-20260816-001`.

DATE: `2026-08-16`

BRANCH: `codex/bugfix-05b-erp-hierarchy-reader`

BASE SHA: `8267a23ae157320026d0bacbc111213ed71e5f4c`

FINAL IMPLEMENTATION SHA: `437275acb7d378b069a0352e3ec3d48e95aa54d2`

STATUS: `READY FOR COORDINATOR QA / NO MERGE / NO LIVE WRITE`

`FINAL IMPLEMENTATION SHA` содержит код и тесты. Этот handoff добавляется отдельным documentation-only commit и не меняет проверенную реализацию.

## Что изменено

- Добавлена внутренняя immutable-модель `OrganizationHierarchyNode` с полями `id`, `name`, `code`, `parent_id`, `level`, `type`.
- Добавлен `ERPOrganizationHierarchyReader`, который строит семантическую цепочку `точное сокращённое подразделение → родительское подразделение → юридическая организация` из явных полей ERP-выгрузки.
- Добавлены exact-only поиск элемента, подъём по родителям и определение корневой организации.
- Добавлены `OrganizationReferenceResolution` и `ExactOrganizationReferenceResolver` с DTO-полями `department`, `cfo`, `cfo_code`, `organization`, `organization_code`.
- Существующий `ExactOrganizationHierarchyResolver` переведён на новую модель без изменения его внешнего контракта.
- Для packaged-каталогов, созданных до сохранения трёх явных ERP-полей, оставлен точный fallback только внутри явно выбранной ветки организации.

## Что сохранено

- UI и export schema не изменены.
- Application workflow, persistence, RUN/snapshot и single-flight логика не изменены.
- Не добавлены `contains`, `startswith`, fuzzy, case-folding, похожие названия или выбор первого результата.
- При нескольких одинаковых exact-наименованиях resolver возвращает отсутствие решения, а не выбирает кандидата.
- ADO/ODBC/1C/DB write, live write, merge, release и PR не выполнялись.
- `ОрганизациииерархияЕРП.xlsx` прочитан только read-only вне репозитория и не добавлен в Git.

## Тесты и checks

```text
python -m pytest -q
183 passed, 6 skipped, 1 warning

python -m pytest -q tests/unit/test_organization_hierarchy.py tests/integration/test_organization_reference_enrichment.py
15 passed

python -m compileall -q src tests scripts
PASS

git diff --check
PASS

git ls-files -- '*.xlsx'
empty
```

Добавлены требуемые тесты:

- `test_find_exact_department`;
- `test_parent_traversal`;
- `test_root_organization_resolution`.

Дополнительно проверены exact top-level lookup, отказ при неоднозначном exact-name и DTO с обоими кодами.

## Read-only real-file evidence

```text
file: ОрганизациииерархияЕРП.xlsx
SHA-256: 3342603C0782FE12871AD55E7E19E778A97651E8CFF2E00F0CE6774295C57522
parsed reference nodes: 357
built hierarchy nodes: 459
```

Проверенные реальные цепочки:

```text
ХП Отдел по управлению персоналом
→ Департамент по управлению персоналом
→ ООО "Хладокомбинат "Пригородный"
codes: 000000196 / 000000192

АЮ Отдел обеспечения
→ Департамент обеспечения
→ ООО "Айс Юнион"
codes: 000000175 / 000000001
```

## Feature Baseline result

- `CHANGED_AUTHORIZED`: внутреннее построение дерева по `ORG-001` и exact ERP-resolution по `MAP-001` в пределах TASK-05B.
- `PRESERVED`: все остальные Feature Baseline invariants, включая normal UI, экспорт, structural input detection, immutable RUN-local snapshot, idempotency и `NO_LIVE_WRITE`.

## Риски и ограничения

- Exact-name без одного однозначного элемента намеренно не разрешается.
- Узел без ERP-кода остаётся в дереве с пустым `code`; существующий workflow сохраняет причину `В ERP-справочнике отсутствует код элемента`.
- В acceptance-примерах задачи есть расхождение с переданным ERP-файлом: `000000173` принадлежит `АЮ Административный отдел`, тогда как `АЮ Отдел обеспечения` имеет код `000000175`; ветка `ХП` ведёт к ООО «Хладокомбинат „Пригородный“», а не к ООО «Айс Юнион». Реализация сохраняет точные значения источника и не подменяет их примерами.
