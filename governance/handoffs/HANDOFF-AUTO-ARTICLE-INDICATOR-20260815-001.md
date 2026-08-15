# Handoff — repeat coordinator QA: automatic article indicators

- Status: `READY_FOR_REPEAT_COORDINATOR_QA_AUTO_INDICATORS`.
- Repository: `fitera2024-rgb/excel-transform-1c`.
- Working branch: `feat/final-owner-smoke-fitera-v2`.
- Draft PR: `#23`, remains Draft and is not merged.
- Previous coordinator head: `ffcb887844638eaac7a059b58150bdc200bb7e34`.
- Canonical base commit: `1b56211630bbc8d3a5ad094b32bb8f9481529c6c` (`integration/baselines-intalev-opiu-v1`).
- Ordinary canonical merge commit: `8b474b380977cbe4ed2a98bf2068913786a34269`.
- Merge parents: `84118cd0bd9a9eadea5deefa805f29ce6ca87975` + `1b56211630bbc8d3a5ad094b32bb8f9481529c6c`.
- Exact tested Windows package head: `48e961a2bf81d003519b15ead757c0fa9682fd64`.
- Coordinator merge/test run: `31861310696`, `SUCCESS`.
- Final package run: `31861503290`, `SUCCESS`.
- Safety: `NO ADO / NO ODBC / NO 1C WRITE / NO LIVE WRITE / NO PR MERGE`.

The governance commit containing this finalized handoff does not change application/package source. Its exact delivery SHA is recorded in Draft PR #23 immediately after publication, avoiding the self-referential impossibility of embedding a commit's own SHA inside its content.

## Canonical baseline integration

Canonical source-CFO and real Intalev behavior is preserved together with CODEX-01:

- persistent exact `(reporting unit, source CFO) -> Intalev CFO source key` mapping;
- persistent exact `Intalev CFO source key -> 1C node` mapping;
- individual and bulk explicit two-stage confirmation;
- persistence across service restart;
- real flat Intalev OPIU hierarchy parser and rejection of generic 12-month matrices;
- canonical tests `test_source_cfo_mapping.py`, `test_source_cfo_mapping_ui.py`, `test_intalev_flat_layout.py`;
- `ArticleIndicatorRule`, `ExactArticleIndicatorMatcher`, `article_indicators` persistence;
- current-RUN rematch without `read_path`;
- exact three-sheet export `OPIU Light / ОПИУ / Показатели` and deterministic indicator aggregation.

The actual Git content conflict was only `src/excel_transform_1c/ui/app.py`. `persistence.py`, `service.py`, `models.py` and `run.html` were auto-merged by Git; overlapping application/model/UI semantics were then reviewed and combined field-by-field rather than using wholesale ours/theirs. Canonical parser/transform/run.js and canonical regression files remain from the normal merge result.

PR #23 changed from `mergeable=false` before integration to `mergeable=true` after the ordinary merge commit. No rebase, squash, force-push or PR merge was performed.

## Empty hierarchy levels

`full_article_path()` keeps an exact three-position path whenever the article level exists, including valid empty hierarchy levels. Example: `Коммерческие расходы →  → Комиссия`.

- Empty business levels are preserved exactly and reversibly in the key.
- `Без группы` is display-only in the business UI and is never written into the business key.
- Exact path is evaluated before unique-name fallback, including an empty group.
- Register/text are not corrected; no fuzzy/contains matching is introduced.

Regression coverage includes:

1. type + empty group + article;
2. same article in different types with empty group;
3. exact path selects the correct indicator;
4. name-only fallback is not used when the exact empty-level path exists.

## Unresolved indicator residue

The compact counters remain. Below them the preview shows one business row per unique unresolved source row with:

- Excel source row (`sheet!row`);
- `Тип → Группа → Статья`;
- ERP code when present;
- status `Не найдено / Неоднозначно / Правило заполнено не полностью`;
- business-readable reason;
- action `Загрузить / дополнить классификатор`.

Technical Rules UI, internal keys, JSON and SQL IDs are not shown. Page progress remains at `Требуются решения` while `indicator_counts.attention > 0`. Classifier supplementation rematches the current RUN and updates counters/list without another `read_path`; `rerun_count` remains zero. Existing CODEX integration coverage continues to compare `OPIU Light` and `ОПИУ` cell-by-cell before/after classifier supplementation.

New repeat-QA tests:

- `tests/unit/test_indicator_empty_hierarchy.py` — 4 empty-level exact-path regressions;
- `tests/integration/test_indicator_unresolved_rows.py` — missing/ambiguous/incomplete business rows plus disappearance after same-RUN rematch with `read_path` forbidden;
- `tests/ui/test_indicator_unresolved_ui.py` — unresolved list and global stage behavior.

## Combined verification

Coordinator run `31861310696` passed all requested commands on the integrated merge tree:

- `git diff --check`: PASS;
- `python -m compileall -q src tests scripts`: PASS;
- `python -m pytest tests/unit -q`: `49 passed`;
- `python -m pytest tests/integration -q`: `51 passed, 5 skipped`;
- `python -m pytest tests/ui -q`: `32 passed`;
- `python -m pytest -q`: `132 passed, 5 skipped`, one external Starlette/TestClient deprecation warning;
- `node --check src/excel_transform_1c/ui/static/run.js`: PASS.

The full suite simultaneously includes canonical real-owner/source-CFO regressions, flat Intalev OPIU parser/rejection behavior, the existing 14 CODEX-01 acceptance areas, empty hierarchy tests and unresolved-indicator business/UI tests.

## Windows offline package

Final package run `31861503290` completed successfully on exact tested package head `48e961a2bf81d003519b15ead757c0fa9682fd64`.

Ubuntu/source gate on the same head:

- unit/integration/UI/full regression: PASS;
- compileall and JavaScript syntax: PASS;
- wheel resource check includes `core/indicator_matching.py` and merged application/core files;
- tracked business Excel: `0`.

Isolated Windows x64 package job:

- application wheel: PASS;
- complete offline wheelhouse: PASS;
- `START_SERVICE` and health/home markers: PASS;
- embedded baseline counts `271 / 357 / 12 / 16`: PASS;
- package functional synthetic transform: 12 monthly records: PASS;
- classifier upload and current-RUN indicator rematch: `automatic=1 / attention=0 / not_found=0`: PASS;
- exact sheet order `OPIU Light / ОПИУ / Показатели`: PASS;
- first two sheets retain 12 data rows and indicator sheet contains 12 monthly rows: PASS;
- second `START_SERVICE` replaces the first PID and health returns OK: PASS;
- `STOP_SERVICE` releases the service: PASS;
- ZIP integrity: PASS.

The exact two-stage source-CFO semantics and persistence are covered by the canonical source-CFO regressions in the same package-head source gate; the Windows wheel built in this run contains the merged `persistence.py`, `service.py`, `models.py`, canonical parser and indicator matcher that passed that gate. No ADO, ODBC, 1C or live database writes were used.

Artifact:

- name: `EXCEL_TO_OPIU_LIGHT_FITERA_FINAL_WINDOWS_V2`;
- artifact id: `9240761147`;
- GitHub artifact digest: `sha256:97a9e20c4fcaaa7ab4962e9a668a51e8fc428c76aa398f4c8cc18494fcdbe92e`;
- inner ZIP: `EXCEL_TO_OPIU_LIGHT_USER_48e961a2bf81.zip`;
- inner ZIP SHA-256: `6ffe5bbfaa5b9775d777f994178f62bf7e58c90ecd20623be875650aedeb66ae`;
- retention through `2026-08-29`.

The artifact was downloaded after CI; `unzip -t` reported no errors and an independent local SHA-256 calculation exactly matched `SHA256.txt` and the Windows job output.

## Delivery gate

- Canonical base is now an ancestor of the branch.
- Draft PR #23 remains open, Draft and unmerged.
- No rebase, squash, history rewrite, force-push or PR merge was performed.
- No ADO / ODBC / 1C write / live write was performed.

`READY_FOR_REPEAT_COORDINATOR_QA_AUTO_INDICATORS`
