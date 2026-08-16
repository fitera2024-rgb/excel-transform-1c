# HANDOFF TASK-05B-02: ERP code resolution

HANDOFF-ID: `HANDOFF-TASK-05B-02-ERP-CODE-RESOLUTION-20260816-001`

TASK-ID: `TASK-05B-02-ERP-CODE-RESOLUTION-20260816-001`

DATE: `2026-08-16`

BRANCH: `codex/task-05b-02-erp-code-resolution`

BASE BRANCH: `codex/bugfix-05b-erp-hierarchy-reader`

BASE SHA: `0f06f2f2db367ace4b7d5ed5086b098cb29f9ce0`

FINAL IMPLEMENTATION SHA: `d4fb7cd33a8bc9d60728a98668e072d4a9ae2d48`

STATUS: `READY FOR COORDINATOR QA / NO MERGE / NO LIVE WRITE`

`FINAL IMPLEMENTATION SHA` содержит код и тесты. Этот handoff добавляется отдельным documentation-only commit и не меняет проверенную реализацию.

## Что изменено

- `ExactOrganizationReferenceResolver` продолжает использовать только `ERPOrganizationHierarchyReader` и exact tree traversal.
- Внутренний `OrganizationReferenceResolution` приведён к контракту TASK-05B-02:
  - `department`;
  - `cfo`;
  - `cfo_code`;
  - `root_organization`;
  - `root_organization_code`.
- Существующий workflow-adapter внутри Business Core читает новые root-поля и сохраняет прежний внешний `OrganizationHierarchyResolution`, поэтому текущий preview/export не изменён.
- Тесты code resolution используют packaged ERP organization baseline и проверяют реальную ветку `000000001`.

## Acceptance result

```text
department:             АЮ Отдел обеспечения
cfo:                    АЮ Отдел обеспечения
cfo_code:               000000175
root_organization:      ООО "Айс Юнион"
root_organization_code: 000000001
```

Проверены отдельные тесты для кода ЦФО, кода головной организации и точного состава DTO.

## Что сохранено

- UI не изменён.
- Excel export и его колонки не изменены; разнос `Организация | Код организации` и `ЦФО | Код ЦФО` остаётся TASK-05B-03.
- Revenue и Quantity не изменены.
- Reference parser, hierarchy model, persistence, RUN/snapshot и single-flight не изменены.
- Не добавлены `contains`, `startswith`, fuzzy, case-folding, похожие названия или first-result fallback.
- ADO/ODBC/1C/DB write, live write, merge, release и PR не выполнялись.
- Реальные `.xlsx` не добавлены в Git.

## Тесты и checks

```text
python -m pytest -q
185 passed, 6 skipped, 1 warning

python -m pytest -q tests/unit/test_organization_hierarchy.py
15 passed

python -m pytest -q tests/integration/test_organization_reference_enrichment.py tests/integration/test_workflow.py
17 passed

python -m compileall -q src tests scripts
PASS

git diff --check
PASS

git ls-files -- '*.xlsx'
empty
```

Единственное warning — существующий `StarletteDeprecationWarning` из `fastapi.testclient`.

## Feature Baseline result

- `CHANGED_AUTHORIZED`: внутренний DTO exact ERP code resolution по TASK-05B-02 / `MAP-001`.
- `PRESERVED`: `ORG-001`, UI/export contracts, Revenue, Quantity, structural input detection, immutable RUN-local snapshot, idempotency и `NO_LIVE_WRITE`.

## Риски и ограничения

- Старые внутренние имена DTO `organization` / `organization_code` заменены на явные `root_organization` / `root_organization_code`; внешние UI/export DTO этой задачей не менялись.
- Missing или ambiguous exact node по-прежнему не получает код автоматически.
- TASK-05B-03 и последующие задачи не выполнялись в этом commit.
