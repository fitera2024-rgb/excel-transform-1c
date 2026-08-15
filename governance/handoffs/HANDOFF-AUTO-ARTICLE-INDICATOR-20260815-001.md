# Handoff — repeat coordinator QA: automatic article indicators

- Status: `PACKAGE_VERIFICATION_IN_PROGRESS`.
- Repository: `fitera2024-rgb/excel-transform-1c`.
- Working branch: `feat/final-owner-smoke-fitera-v2`.
- Draft PR: `#23`, remains Draft and is not merged.
- Previous coordinator head: `ffcb887844638eaac7a059b58150bdc200bb7e34`.
- Canonical base commit: `1b56211630bbc8d3a5ad094b32bb8f9481529c6c` (`integration/baselines-intalev-opiu-v1`).
- Ordinary canonical merge commit: `8b474b380977cbe4ed2a98bf2068913786a34269`.
- Merge parents: `84118cd0bd9a9eadea5deefa805f29ce6ca87975` + `1b56211630bbc8d3a5ad094b32bb8f9481529c6c`.
- Coordinator merge/test run: `31861310696`, `SUCCESS`.
- Safety: `NO ADO / NO ODBC / NO 1C WRITE / NO LIVE WRITE / NO PR MERGE`.

## Canonical baseline integration

Canonical source-CFO and real Intalev behavior is preserved together with CODEX-01:

- persistent exact `(reporting unit, source CFO) -> Intalev CFO source key` mapping;
- persistent exact `Intalev CFO source key -> 1C node` mapping;
- individual and bulk explicit two-stage confirmation;
- persistence across service restart;
- real flat Intalev OPIU hierarchy parser and rejection of generic 12-month matrices;
- `ArticleIndicatorRule`, `ExactArticleIndicatorMatcher`, `article_indicators` persistence;
- current-RUN rematch without `read_path`;
- exact three-sheet export `OPIU Light / ОПИУ / Показатели` and deterministic indicator aggregation.

The actual Git content conflict was `src/excel_transform_1c/ui/app.py`. `persistence.py`, `service.py`, `models.py` and `run.html` were auto-merged by Git; overlapping application/model/UI semantics were then reviewed and combined field-by-field rather than using wholesale ours/theirs. Canonical parser/transform/run.js and the three canonical regression files remain from the normal merge result.

## Empty hierarchy levels

`full_article_path()` now keeps an exact three-position path whenever the article level exists, including valid empty hierarchy levels. Example: `Коммерческие расходы →  → Комиссия`.

- Empty business levels are preserved exactly and reversibly in the key.
- `Без группы` is display-only in the business UI and is never written into the business key.
- Exact path is evaluated before unique-name fallback, including an empty group.
- No fuzzy/contains/case correction is introduced.

Regression coverage includes type + empty group + article, same-name articles in different types with empty groups, correct indicator selection by exact path, and proof that name-only is not used when the exact empty-level path exists.

## Unresolved indicator residue

The compact counters remain. Below them the preview shows one business row per unique unresolved source row with:

- Excel source row (`sheet!row`);
- `Тип → Группа → Статья`;
- ERP code when present;
- status `Не найдено / Неоднозначно / Правило заполнено не полностью`;
- business-readable reason;
- action `Загрузить / дополнить классификатор`.

Technical Rules UI, internal keys, JSON and SQL IDs are not shown. Page progress remains at `Требуются решения` while `indicator_counts.attention > 0`. Classifier supplementation rematches the current RUN and updates counters/list without another `read_path`; `rerun_count` remains zero. Existing integration coverage continues to compare `OPIU Light` and `ОПИУ` cell-by-cell before/after classifier supplementation.

## Combined verification

Coordinator run `31861310696` passed all requested commands:

- `git diff --check`: PASS;
- `python -m compileall -q src tests scripts`: PASS;
- `python -m pytest tests/unit -q`: `49 passed`;
- `python -m pytest tests/integration -q`: `51 passed, 5 skipped`;
- `python -m pytest tests/ui -q`: `32 passed`;
- `python -m pytest -q`: `132 passed, 5 skipped`, one external Starlette/TestClient deprecation warning;
- `node --check src/excel_transform_1c/ui/static/run.js`: PASS.

The suite simultaneously contains the canonical source-CFO regressions, flat Intalev parser regression, all existing CODEX-01 acceptance coverage, four empty-hierarchy tests and unresolved-indicator business/UI tests.

## Windows offline package

A new package verification run is intentionally triggered by this governance commit after the successful canonical merge. The final run ID, exact tested package head, artifact ID, inner ZIP name and SHA-256 will be filled in after that isolated Windows run completes.

Required package checks: `START_SERVICE`, embedded `271 / 357 / 12 / 16`, exact source CFO two-stage behavior through the merged regression suite, classifier upload/current-RUN rematch, exact three sheets, restart persistence, `STOP_SERVICE`, ZIP integrity and checksum.

## Delivery rule

The exact implementation merge authority is `8b474b380977cbe4ed2a98bf2068913786a34269`. The final governance-only delivery head is recorded in Draft PR #23 after the package evidence is written here; no history is rewritten and the PR is not merged.
