# CODEX-03 — формулы ОПИУ ERP и построитель классификатора

STATUS: `READY_FOR_IMPLEMENTATION / OWNER_ACCEPTED / RISK_L / DRAFT / NO_MERGE / NO_LIVE_WRITE`

## Git authority

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Working branch: `work/opiu-erp-formula-rule-builder-v1`.
- Parent product head: `feat/final-owner-smoke-fitera-v2@b712cadba6d035108c56dcc9746ff42443c3b07c`.
- Exact task base is the commit that adds `governance/tasks/TASK-READY-CODEX-03-20260815-001.md`.

Before any implementation change run:

```text
git status --short --branch
git branch --show-current
git rev-parse HEAD
git log -1 --format=%H -- governance/tasks/TASK-READY-CODEX-03-20260815-001.md
```

The last two SHA values must be identical. If branch or SHA differs, change nothing and return:

`CHECKOUT_BLOCKED_CODEX_03`

## Owner business decision

The report indicator is determined by the **disclosure group** (`группа раскрытия`). An article name by itself is not authoritative.

Business chain:

```text
OPIU formula
→ disclosure group
→ article selection inside that disclosure group
→ formula filters and source
→ report indicator
→ required analytics
```

The same article may belong to different indicators under different disclosure groups. Therefore a simple global mapping `article → indicator` is forbidden.

Example:

```text
Disclosure group: Administrative
Article: Internet
→ Indicator: Administrative

Disclosure group: Production
Article: Internet
→ Indicator: Production
```

## Owner evidence files

Analyze the exact owner-supplied files outside Git:

- `Источники для ОПИУ_ ЕРП.mxl`;
- `ПоказателиОтчетов_ОПИУ_ЕРП.xlsx`;
- `ОПИУ ФОРМУЛЫ.xlsx`;
- `ОПИУ аНАЛИТИКИ.xlsx`;
- `Регионы.xlsx`;
- `СЕТИ.xlsx`.

Do not commit these files, converted copies, row-level dumps, formulas containing sensitive values, runtime databases, or generated financial outputs.

If one or more files are not visible in the task environment, do not invent their contents. Return:

`OWNER_FILES_NOT_VISIBLE_CODEX_03`

and list the missing exact filenames.

## Objective

Build a small, deterministic OPIU ERP knowledge layer that can later replace the temporary manually uploaded `article → indicator` classifier.

CODEX-03 must:

1. structurally read the six owner sources;
2. model formula conditions without flattening their business meaning;
3. derive deterministic candidate rules keyed first by disclosure group and then by article selection within that group;
4. attach exact report indicator and required analytics where the sources prove them;
5. classify every derived rule as `resolved`, `missing`, `ambiguous`, `incomplete`, or `unsupported`;
6. produce a coverage report and a Git-visible handoff;
7. keep current UI, current upload workflow, and current three-sheet export unchanged.

## Scope boundary

This task is **rule discovery and Business Core construction only**.

Do not yet:

- replace the current article-indicator classifier in the user workflow;
- change the preview UI;
- change `OPIU Light`, `ОПИУ`, or `Показатели` export semantics;
- add ADO, ODBC, SQL, 1C write, or live write;
- add a heavy generic Rules Engine;
- expose technical formulas or internal identifiers to normal users.

A later task will integrate the approved rule catalog into preview and export.

## Source responsibilities

### `ОПИУ ФОРМУЛЫ.xlsx`

Treat as the primary source of report-line calculation logic.

Structurally determine and preserve, where present:

- report row/line identity;
- report row name;
- formula text or formula structure;
- disclosure group;
- article group condition;
- article selection inside the disclosure group;
- source references;
- boolean operators and grouping;
- exclusions and negations;
- constants or coefficients that affect interpretation.

Do not reduce a compound formula to a flat list if that changes meaning.

### `ОПИУ аНАЛИТИКИ.xlsx`

Determine exact required dimensions for each report row/rule, including only those proven by the file, for example:

- organization;
- CFO;
- region;
- network;
- nomenclature;
- other explicit analytics.

### `ПоказателиОтчетов_ОПИУ_ЕРП.xlsx`

Build the exact report-indicator catalog from proven fields:

- stable indicator code;
- indicator name;
- report row identity;
- indicator grouping or hierarchy;
- analytic group where present.

Do not infer an article mapping from an empty or unrelated column.

### `Источники для ОПИУ_ ЕРП.mxl`

Detect actual content format structurally, not from `.mxl` filename alone.

Extract only supported, proven fields such as:

- source code/identity;
- source type;
- register/account/source reference;
- consumer/report indicator reference;
- source filters and analytics.

If part of the MXL grammar is unsupported, preserve the source fragment as an unsupported condition and mark the corresponding rule `unsupported`; do not silently ignore it.

### `Регионы.xlsx` and `СЕТИ.xlsx`

Build exact catalogs and surface conflicts.

Do not assume code-only or name-only uniqueness unless proven. Where duplicates exist, use a proven compound identity or mark ambiguity.

## Required Business Core model

Create a small module, for example:

```text
src/excel_transform_1c/core/opiu_formula_rules.py
```

or a focused package under:

```text
src/excel_transform_1c/core/opiu_rules/
```

The core must not depend on UI objects, filesystem paths, SQLite connections, openpyxl workbooks, or ADO connection objects.

Required public DTOs should cover at least:

### `OPIUFormulaRule`

- stable rule identity;
- report line identity;
- report indicator code/name;
- disclosure group exact value;
- article group exact value where separate;
- article selector exact value/code/path;
- source identity;
- normalized condition tree or typed condition list;
- required analytics;
- status;
- business-readable reason.

### `OPIURuleMatchKey`

The key must preserve:

1. disclosure group — mandatory for automatic resolution;
2. article identity inside the group;
3. exact source/formula conditions needed to disambiguate;
4. required analytics that participate in selection.

Do not put display labels such as `Без группы` into business keys. Empty source levels must remain exact and reversible.

## Matching semantics

Automatic resolution is allowed only when the sources prove exactly one complete rule.

Required order:

1. exact disclosure group;
2. exact article code/path/name inside that disclosure group;
3. exact formula/source conditions;
4. exact required analytic values when they participate in the formula;
5. exactly one report indicator.

Statuses:

- `resolved`: one complete exact rule;
- `missing`: no rule;
- `ambiguous`: more than one complete exact rule;
- `incomplete`: rule exists but required indicator/source/analytics are missing;
- `unsupported`: source syntax or condition cannot be interpreted safely.

Forbidden:

- global article-name-only matching;
- fuzzy matching;
- contains/substring matching;
- case correction;
- typo correction;
- first-candidate selection;
- filename heuristics;
- silently dropping unsupported formula conditions.

Technical trimming of surrounding spaces is allowed only when original values remain available and semantics are not changed.

## Formula condition model

Do not store formulas only as opaque strings when supported structure can be extracted.

Use typed conditions such as:

- equality/inequality;
- membership in a set;
- disclosure-group condition;
- article-group condition;
- article condition;
- source/register/account condition;
- region/network/CFO/organization analytic condition;
- conjunction/disjunction;
- exclusion/negation;
- unsupported fragment.

The parser must preserve boolean grouping. `A AND (B OR C)` must not become `(A AND B) OR C`.

## Coverage report

Generate a non-Git owner artifact:

`OPIU_RULE_COVERAGE_REPORT.xlsx`

with at least these sheets:

### `Rules`

- report line;
- indicator code/name;
- disclosure group;
- article selector;
- source;
- required analytics;
- status;
- business-readable reason.

### `Unresolved`

- report line;
- disclosure group;
- article selector;
- status;
- exact reason;
- required owner action.

### `Analytics`

- report indicator;
- required analytic;
- source file/section;
- status.

### `Source coverage`

- source identity;
- referenced by formulas;
- found in MXL source catalog;
- status/reason.

Do not include raw financial amounts or machine paths.

## Tests

Add synthetic unit tests for at least:

1. same article under two disclosure groups resolves to two different indicators;
2. article without disclosure group does not auto-resolve;
3. exact disclosure group + exact article resolves one rule;
4. two exact rules remain ambiguous;
5. empty hierarchy level is preserved exactly;
6. formula AND/OR grouping is preserved;
7. exclusion/negation changes rule meaning;
8. source condition disambiguates two rules;
9. region condition disambiguates two rules;
10. network condition disambiguates two rules;
11. unsupported syntax becomes `unsupported`;
12. missing indicator becomes `incomplete`;
13. no fuzzy/case/contains fallback;
14. deterministic output independent of source row order.

Add integration tests, using owner files only outside Git when available, for:

- structural parsing of each supplied XLSX;
- structural parsing or fail-closed handling of MXL;
- formula-to-indicator linkage;
- formula-to-analytics linkage;
- region/network catalog conflict reporting;
- generation and reopening of `OPIU_RULE_COVERAGE_REPORT.xlsx`;
- zero tracked business Excel/MXL files.

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

Existing service regression must stay green even though UI/export are not changed.

## Deliverables

1. Code and tests on `work/opiu-erp-formula-rule-builder-v1`.
2. Draft PR:

```text
work/opiu-erp-formula-rule-builder-v1
→ feat/final-owner-smoke-fitera-v2
```

3. Handoff:

`governance/handoffs/HANDOFF-OPIU-ERP-FORMULA-RULE-BUILDER-20260815-001.md`

The handoff must include:

- exact task base and final head;
- actual detected structure of each owner file;
- supported formula grammar;
- unsupported formula fragments;
- rule counts by status;
- source coverage counts;
- analytic coverage counts;
- conflicts in region/network catalogs;
- changed files;
- test counts and CI run ID;
- coverage artifact name/checksum;
- explicit confirmation that owner files, formulas dumps, amounts, passwords, databases, and live-write code were not committed.

4. Update the Draft PR description with the same concise evidence.

Do not merge.

Final marker:

`READY_FOR_COORDINATOR_QA_OPIU_RULES`

`NO ADO / NO ODBC / NO 1C WRITE / NO LIVE WRITE / NO MERGE`.
