# Active Work

STATUS: `DISCOVERY / EXCEL_LOGIC_HANDOFF_READY / USER_FLOW_NOT_ACCEPTED`

## Current phase

Новый сервис находится на этапе завершения Product Contract и owner review User Flow.

Актуальный handoff:

`governance/handoffs/HANDOFF-EXCEL-LOGIC-20260812-001.md`

Предыдущий handoff `HANDOFF-COORDINATOR-20260811-001.md` остаётся историческим источником раннего discovery, но latest Excel/reference decisions находятся в новом handoff и канонических документах.

## Completed discovery

Исследованы и сверены:

- реальный бюджетный Excel ПС и его 20 листов;
- подготовленный диапазон расходов: 179 строк, 12 месяцев;
- sample normalized result АЮ;
- актуальный ERP-справочник статей и coverage 179 строк;
- сценарии;
- периоды;
- показатели отчётов ОПИУ;
- виды отчётов;
- вложенная иерархия организаций/ЦФО/подразделений;
- screenshot дерева `Организации` в 1С;
- текущие Git documents, branch и Draft PR.

Принятые решения перенесены в:

- `docs/PRODUCT.md`;
- `docs/USER_FLOW.md`;
- `governance/DECISIONS.md`;
- `governance/FEATURE_BASELINE.md`;
- `governance/handoffs/HANDOFF-EXCEL-LOGIC-20260812-001.md`.

## Current owner gate

До implementation требуется:

1. Закрыть оставшиеся действительно необходимые Product Contract решения по одному.
2. Явно принять User Flow владельцем.

Самый следующий owner decision:

`OWNER_DECISION_REPORT_TYPE`

Выбрать один вид отчёта V1:

- `Отчет о прибылях и убытках`, код `ОтчетОПрибыляхИУбытках`;
- либо `ОПИУ`, код `ОПИУ`.

После этого последовательно закрываются scenario identity, period identity/filter, organization mapping/status, delegation target, mapping reuse context и negative amount rule.

## Forbidden now

- начинать product implementation до owner acceptance User Flow;
- подключать ADO live write;
- писать в TEST/PROD 1С;
- делать прямой SQL-write во внутренние таблицы 1С;
- merge Draft PR координатором;
- копировать тяжёлые OPIU controls или раздувать локальный конвертер до platform architecture;
- переоткрывать ACCEPTED-решения без нового evidence или явного owner decision.

## Git work

- Repository: `fitera2024-rgb/excel-transform-1c`.
- Working branch: `coord/proportional-safety-local-converter`.
- Draft PR: `#1`.
- Main at reconciliation start: `9af5ac112d06e6e6ed8c5e1bc4261eaaa099c607`.
- Branch head before Excel-logic handoff commit: `686f02dc8829f22093cc8cc23b8a31544aec5b7a`.
- Merge: not performed.
- ADO/live write: not performed.

Точный итоговый head после этого docs-only handoff является текущим head Draft PR и возвращается владельцу в delivery-ответе.
