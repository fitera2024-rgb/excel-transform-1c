# CODEX-02 — каноническое объединение и повторная QA показателей

STATUS: `READY_FOR_IMPLEMENTATION / OWNER_ACCEPTED / RISK_M / DRAFT / NO_MERGE / NO_LIVE_WRITE`

## Git authority

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Working branch: `feat/final-owner-smoke-fitera-v2`.
- CODEX-01 final head before this task: `ffcb887844638eaac7a059b58150bdc200bb7e34`.
- Canonical commit to integrate: `1b56211630bbc8d3a5ad094b32bb8f9481529c6c` from `integration/baselines-intalev-opiu-v1`.
- Draft PR: `#23`.

Exact task base is the commit that adds:

`governance/tasks/TASK-READY-CODEX-02-20260815-001.md`

Before any change run:

```text
git status --short --branch
git branch --show-current
git rev-parse HEAD
git log -1 --format=%H -- governance/tasks/TASK-READY-CODEX-02-20260815-001.md
```

The last two SHA values must be identical. Otherwise change nothing and return:

`CHECKOUT_BLOCKED_CODEX_02`

## Objective

Integrate CODEX-01 into the latest canonical owner-smoke tree and close the coordinator findings without changing accepted business meaning.

## 1. Merge the canonical owner-smoke commit

Create a normal merge commit that integrates:

`1b56211630bbc8d3a5ad094b32bb8f9481529c6c`

Do not rebase, squash, force-push, rewrite history, or resolve conflicting files wholesale with ours/theirs.

Preserve from the canonical commit:

- exact two-stage CFO chain:
  `source reporting unit + source CFO → Intalev CFO → exact 1C node`;
- `source_cfo_mappings` persistence and restart reuse;
- individual and bulk two-stage CFO confirmation;
- real flat Intalev OPIU hierarchy parser;
- rejection of a generic 12-month matrix as Intalev OPIU;
- tests:
  `tests/integration/test_source_cfo_mapping.py`,
  `tests/ui/test_source_cfo_mapping_ui.py`,
  `tests/unit/test_intalev_flat_layout.py`.

Preserve from CODEX-01:

- `ArticleIndicatorRule`;
- `ExactArticleIndicatorMatcher`;
- locally persisted `article_indicators` classifier;
- current-RUN rematch without rereading the input Excel;
- exact priority:
  `ERP code → exact full path → globally unique exact name`;
- three export sheets in this order:
  `OPIU Light`, `ОПИУ`, `Показатели`;
- deterministic indicator aggregation;
- compact business UI without technical Rules.

## 2. Exact path with empty business hierarchy levels

An empty group or another allowed empty business level must remain an exact and reversible part of the key.

Requirements:

- do not replace source empty value with the display label `Без группы` in a key;
- do not discard the full path because one level is empty;
- do not fall back to name-only when an exact path with an empty level can be built;
- do not change case or text;
- no typo correction, contains, fuzzy, or first-candidate selection.

Add regression tests for:

1. expense type + empty group + article;
2. the same article name under two different expense types with an empty group;
3. exact full-path selection of the correct indicator;
4. proof that name-only fallback is not used in this case.

## 3. Show unresolved indicator residue

Keep the compact counters, but add a business-readable list of unresolved source rows.

For each unique source row show:

- Excel source row number;
- exact business path `Тип → Группа → Статья`;
- ERP code when present;
- business status:
  `Не найдено`, `Неоднозначно`, or `Правило заполнено не полностью`;
- clear reason;
- one action: `Загрузить / дополнить классификатор`.

Do not restore a technical Rules editor. Do not expose JSON, internal keys, SQLite IDs, or filesystem paths.

The page progress must not say `Проверка завершена` while `indicator_counts.attention > 0`.

After the classifier is supplemented, the current RUN list and counters must refresh without rereading the original Excel and without increasing `rerun_count`.

Add UI/integration tests for:

- missing;
- ambiguous;
- incomplete;
- unresolved item disappears after classifier supplement;
- no repeated `read_path`;
- `OPIU Light` and `ОПИУ` stay cell-by-cell unchanged.

## 4. Boundaries

Do not include the newly supplied ERP MXL/formula/analytics/region/network sources in CODEX-02. They belong to the next sequential task after CODEX-02 is accepted.

Do not change:

- live-write boundaries;
- ADO/ODBC/1C write paths;
- legacy/protected intake semantics except mechanical conflict resolution;
- exact ERP hierarchy semantics;
- port cleanup or launcher unless a merge conflict requires a mechanical preservation.

## 5. Verification

Run:

```text
git diff --check
python -m compileall -q src tests scripts
python -m pytest tests/unit -q
python -m pytest tests/integration -q
python -m pytest tests/ui -q
python -m pytest -q
node --check src/excel_transform_1c/ui/static/run.js
```

The combined suite must include:

- canonical real-owner regressions;
- two-stage source CFO mapping;
- flat Intalev OPIU parsing;
- all CODEX-01 acceptance tests;
- empty hierarchy indicator tests;
- unresolved indicator UI tests.

Build a new offline Windows package and smoke-test:

- `START_SERVICE`;
- built-in counts `271 / 357 / 12 / 16`;
- source CFO → Intalev CFO → 1C mapping;
- classifier upload and same-RUN rematch;
- exact three-sheet export;
- restart;
- `STOP_SERVICE`;
- ZIP integrity.

## 6. Delivery

Update:

- Draft PR `#23`;
- `governance/handoffs/HANDOFF-AUTO-ARTICLE-INDICATOR-20260815-001.md`.

The handoff must include:

- previous head;
- canonical commit;
- merge commit and both parents;
- exact final head;
- conflict resolutions;
- test counts;
- CI run ID;
- package filename and SHA-256;
- confirmation that no real Excel and no live write were added.

Do not merge.

Final marker:

`READY_FOR_REPEAT_COORDINATOR_QA_AUTO_INDICATORS`

`NO ADO / NO ODBC / NO 1C WRITE / NO LIVE WRITE / NO MERGE`.
