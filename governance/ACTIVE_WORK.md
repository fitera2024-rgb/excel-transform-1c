# Active Work

STATUS: `OPIU_ERP_RULES_INTEGRATION / REAL_OWNER_SMOKE_PASSED_WITH_ATTENTION / CI_PENDING / DRAFT / NO_MERGE / NO_LIVE_WRITE`

## Current vertical slice

`Built-in references → content-based Excel preparation → exact ERP/tax/CFO decisions → formula-derived disclosure-group rules → 12-month preview → three-sheet XLSX export`

## Git authority

- Latest product parent: `feat/final-owner-smoke-fitera-v2@b712cadba6d035108c56dcc9746ff42443c3b07c`.
- Recovered CODEX-03 parent: `recovery/codex-03-opiu-rules-20260815@63d2e35244ae3fccc82bdef4fd1d702979219ad0`.
- Integration target: `integration/opiu-erp-rules-v1`.
- PR #23 remains Draft and unmerged; the OPIU-rule integration must use a separate Draft PR.

## Owner decision

The indicator is determined by the exact disclosure group, then the exact article inside that group, then supported exact formula/source conditions. Article-only, fuzzy, contains, typo and case-corrected matching are forbidden.

## Implemented in the integration worktree

- six-source OPIU ERP rule builder and persistence;
- full disclosure hierarchy resolver with deepest exact group priority;
- fail-closed unsupported formula/source conditions;
- one-time business upload form for formulas, analytics, ERP indicators, MXL sources, regions and networks;
- formula-derived indicator export without inventing a sales channel;
- existing two-stage source CFO → Intalev CFO → 1C node behavior preserved;
- protected/legacy intake and three-sheet export preserved.

## Real smoke

- AY: 195 source rows; 189 automatically classified; 6 attention; 60 aggregated indicator rows.
- PV: 184 source rows; 179 automatically classified; 5 attention; 60 aggregated indicator rows.
- annual Intalev OPIU remains readable/exportable; unsupported ERP disclosure identity stays attention.

## Next gate

- publish exact two-parent integration commit;
- full GitHub CI;
- Windows offline package start/HTTP flow/transform/restart/stop;
- package checksum verification;
- Owner UX Smoke.

## Forbidden

- merge without owner acceptance;
- ADO/ODBC/1C/live write;
- owner source files or runtime databases in Git;
- fuzzy or guessed indicators;
- removal or schema change of `OPIU Light` and `ОПИУ`.
