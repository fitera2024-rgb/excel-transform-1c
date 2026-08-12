# RESEARCH TASK — ERP mapping mismatches in AY and PV budgets

TASK-ID: `RESEARCH-ERP-MAPPING-AY-PV-20260813-001`  
DATE: `2026-08-13`  
REPOSITORY: `fitera2024-rgb/excel-transform-1c`  
ISSUE: `#5`  
BRANCH: `research/erp-mapping-ay-pv`  
BASE: `e96fb403da7b96a5707ba131cb141788fe27bde3`  
RISK: `L — financial semantics analysis`  
STATUS: `READY_FOR_ANALYSIS / READ_ONLY / NO_CODE_CHANGE / NO_LIVE_WRITE`

## Business question

Why do rows of the real AY and PV budget workbooks fail or conflict during exact ERP article matching, and what is the simplest safe user workflow that can resolve the systemic causes without fuzzy matching or silent correction?

## Inputs supplied outside Git

- `+ГОТОВО АЮ бюджет 2026 от 16.03.xlsx`;
- `+ГОТОВО ПВ бюджет 2026 от 28.01 с новыми налогами+ЭТН.xlsx`;
- the current ERP article catalog used by the local application.

The workbooks are password-protected. The owner supplies the password separately in the interactive session. Never store it in Git, shell history copied into the report, screenshots, logs or artifacts.

## Working method

1. Verify branch and exact base before work.
2. Read `AGENTS.md`, Product Contract, User Flow, Architecture, Decisions, Feature Baseline and current handoffs.
3. Open each real workbook read-only.
4. When necessary, create a temporary decrypted copy outside the repository and delete it after analysis.
5. Do not modify originals.
6. Detect the prepared range structurally; do not rely on filenames or sheet names.
7. Extract each source row exactly as the current service does.
8. Compare source paths with the ERP catalog using exact values first.
9. Do not apply fuzzy matching, typo fixes, case fixes, trimming or normalization to the authoritative result.
10. Additional normalized comparisons are allowed only as diagnostic evidence and must be labelled as hypothetical.

## Required classification

Every source row must receive exactly one primary classification:

- `EXACT_UNIQUE`;
- `EXACT_MULTIPLE`;
- `NAME_ONLY_UNIQUE`;
- `NAME_ONLY_MULTIPLE`;
- `NO_EXACT_NAME`;
- `SAFE_TEXT_DIFFERENCE`;
- `SOURCE_STRUCTURE_PROBLEM`;
- `REFERENCE_PARSE_PROBLEM`;
- `MANUAL_MAPPING_CONFLICT`.

The exact matching key is:

`report type → expense type → expense group → source article`.

## Required checks

- leading/trailing and non-breaking spaces;
- line breaks and invisible characters;
- hyphen/dash and quotation-mark differences;
- case-only differences;
- repeated names in different branches;
- empty or shifted hierarchy fields;
- duplicate ERP codes and duplicate full paths;
- `Удалить` / `!!!Удалить` branches without automatic exclusion;
- persisted manual mappings;
- differences between AY and PV;
- systemic parser/source-column errors;
- whether one shared cause explains a large part of the mismatches.

## Required outputs

Create only:

`governance/research/RESEARCH-ERP-MAPPING-AY-PV-20260813-001.md`

The report must contain:

1. exact base/head and analysis date;
2. read-only/decryption method;
3. actual ranges and source-row counts;
4. classification totals separately for AY and PV;
5. reconciliation showing that totals equal the actual row counts;
6. top systemic causes;
7. up to 20 representative examples without amounts, personal data, passwords or local paths;
8. two to four simplification options;
9. coverage and risk of each option;
10. recommended option;
11. exact owner decisions still required;
12. confirmation that no real workbook, decrypted copy, password or row-level extract entered Git.

A single Draft PR containing only this Markdown report is allowed.

## Recommendation options to evaluate

At minimum evaluate:

- exact full path plus explicit manual selection;
- a narrow, explicit normalization allowlist with visible attention status;
- hierarchical selection `expense type → group → article → ERP code`;
- persistent confirmed mapping by full business context;
- parser/source extraction correction when evidence shows a structural defect.

## Acceptance criteria

- totals reconcile for each workbook;
- each mismatch has one primary category;
- facts and hypotheses are separated;
- no code or test changes;
- no working database mutation;
- no ADO/1C/TEST/PROD write;
- no fuzzy/autofix;
- no real files or secrets in Git;
- final status: `RESEARCH_READY_FOR_OWNER_DECISION`.

## Final response

Post the Draft PR number, exact head and a five-line executive summary to Issue #5. Do not merge.