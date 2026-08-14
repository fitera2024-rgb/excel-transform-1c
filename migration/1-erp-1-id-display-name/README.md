# Cloud handoff: `1-erp-1-id-display-name`

This directory transfers the exact safe working-tree payload recovered from the user's desktop Codex archive.

## Git authority

- Repository: `fitera2024-rgb/excel-transform-1c`
- Parent/base commit: `5023ebb21bd6d9138ccc19ce3c2acf5e8b50db48`
- Work branch: `work/baseline-catalogs-v1`
- PR target: `feat/baselines-intalev-opiu-repair`
- Payload TAR.XZ SHA-256: `990f565d703751df4ee8768440e29dac3b878cccf7f3b3baa5333d9d0476c006`

## Exact payload scope

1. `src/excel_transform_1c/adapters/persistence.py`
2. `src/excel_transform_1c/adapters/references.py`
3. `src/excel_transform_1c/baselines/__init__.py`
4. `src/excel_transform_1c/baselines/erp_articles.json`
5. `src/excel_transform_1c/baselines/intalev_cfos.json`
6. `src/excel_transform_1c/baselines/manifest.json`
7. `src/excel_transform_1c/baselines/organizations.json`
8. `src/excel_transform_1c/baselines/scenarios.json`

No Excel source books, passwords, tokens, runtime databases, local absolute paths, or user financial rows are included. The embedded catalogs contain 271 unique ERP article codes, 357 unique organization node IDs, 12 unique scenario name/year keys, and 15 unique Intalev CFO source keys.

## Cloud Codex procedure

1. Run `python migration/1-erp-1-id-display-name/apply_payload.py`.
2. Review only the eight exact payload paths; do not retain the handoff payload in the final implementation commit.
3. Reconcile the implementation with current tests and packaging. In particular, verify baseline bootstrap behavior for empty temporary stores and make sure baseline JSON resources are included in built distributions.
4. Run compile, targeted tests, and full regression.
5. Commit the actual source changes to this same branch.
6. Remove `migration/1-erp-1-id-display-name/` after the source payload is safely committed.
7. Keep the PR Draft. No merge, release, ADO, ODBC, 1C, or live write.

## Pre-transfer verification

- `python -m compileall -q src tests`: PASS.
- Targeted test run after supplying the missing test dependency: 21 passed, 3 failed.
- The three failures show that unconditional baseline bootstrap changes legacy tests that assumed an empty new store. This is an unfinished implementation concern for Cloud Codex, not hidden as PASS.
