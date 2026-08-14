# Handoff — Legacy Excel intake V1

STATUS: `READY_FOR_INTEGRATION_INTAKE`
BRANCH: `work/legacy-excel-intake-v1`
TARGET: `feat/baselines-intalev-opiu-repair`
START BASE: `5023ebb21bd6d9138ccc19ce3c2acf5e8b50db48`
SAFETY: `NO ADO / NO LIVE WRITE / NO MERGE`

## Changed

- Excel container type is detected from signatures and required internal parts rather than the filename suffix.
- Ordinary OOXML, legacy BIFF, encrypted OOXML and legacy SpreadsheetML XML are distinct intake types.
- Every unprotected input keeps its exact original bytes and receives a separate OOXML working copy; an ordinary valid OOXML copy is byte-identical.
- Legacy BIFF and SpreadsheetML are converted locally to an OOXML working copy without requiring Microsoft Excel.
- Recoverable OOXML ZIP/XML damage is repaired conservatively into a separate deterministic working copy.
- Repair rejects unsafe member paths, duplicate members, unsupported compression, oversized packages, corrupt required parts and ambiguous XML damage.
- Encrypted OOXML remains handled by the narrow password adapter. A legacy BIFF OLE container is no longer mistaken for an encrypted OOXML container.
- Password values remain request-local and are not added to result objects, persistence, filenames, logs, Git or this handoff.

## Preserved

- Application workflow, persistence semantics, reference parsing, Intalev business parsing, UI, export and ADO were not changed.
- Structural range detection, cached-value reading, exact ERP mapping, tax/CFO workflows, preview and export behavior are unchanged.
- No real workbook, workbook content, credential or local runtime artifact is tracked.
- No merge or live write was performed.

## Dependencies

- `xlrd` reads legacy BIFF `.xls` content.
- `olefile` classifies OLE streams so encrypted OOXML and BIFF stay distinct.
- `xlwt` is test-only and creates synthetic BIFF fixtures.

## Test evidence

- `git diff --check` — PASS.
- `python -m compileall -q src tests` — PASS.
- `python -m pytest tests/unit -q` — `30 passed`.
- `python -m pytest tests/integration -q` — `32 passed, 4 skipped`.
- `python -m pytest -q` — `87 passed, 4 skipped` with one existing Starlette deprecation warning.
- Real OPIU-shaped local workbook intake smoke — PASS when a local candidate was available.
- Real CFO smoke — SKIPPED because no specifically identifiable local candidate was available.
- Real protected AY/PV smoke — conditional and credential-free; synthetic AY/PV regression passed.
- Git tracked Excel inventory — empty.

The four conditional skips are explicitly gated real-file smoke tests. They activate only when the corresponding local environment values are supplied and never disclose their values.

## Risks and limits

- Legacy conversion preserves cell values required by intake, not workbook styling, VBA, drawings or legacy formulas as executable formula definitions.
- XML repair is intentionally narrow: illegal control characters and unescaped ampersands can be repaired, while structurally ambiguous damage fails closed.
- Encrypted legacy BIFF and unsupported encryption schemes fail closed.

## Feature Baseline result

- Accepted product, context, mapping, transformation, preview, result and safety invariants: `PRESERVED`.
- Excel intake capability in the authorized scope: `CHANGED_AUTHORIZED`.
- ADO/live write/release approval: `PRESERVED / NOT IMPLEMENTED`.

## Integration

Integrate the exact head recorded by the final commit on this branch into `feat/baselines-intalev-opiu-repair`. The owner/coordinator decides merge separately.

Final marker: `READY_FOR_INTEGRATION_INTAKE`.
