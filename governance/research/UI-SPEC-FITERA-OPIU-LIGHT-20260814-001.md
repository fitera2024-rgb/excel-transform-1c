# UI SPEC — FITERA OPIU Light

## Status

`READY_FOR_INTEGRATION_UI`

## Visual source

The owner-provided `FITERA_SERVICE_UI_STARTER_V2.zip` is used only as a visual and UX reference. Business workflow, endpoints, field names and application semantics remain those of Excel → OPIU Light.

## Header

- thin lime brand line;
- FITERA logo and company name;
- service title `Excel → OPIU Light`;
- explicit local safety status `LOCAL PREVIEW`;
- user-facing boundary: no ERP/1C write.

## Home flow

1. **References and scenarios** — counters, local status, add/extend action.
2. **Business context** — reporting unit, organization hierarchy, scenario, year and period.
3. **Source file and preview** — file, optional password, processing state and one primary action.

All existing form actions, methods, input names, test IDs and JavaScript hooks are preserved.

## Preview

- clear result header and export action;
- four-step result progress indicator;
- compact business statistics;
- separate CFO, ERP and tax confirmation areas;
- attention cards remain grouped by source row;
- confirmed states use green, review states use amber, blocking errors use red;
- tables retain sticky headings and horizontal scrolling.

## States

- success: green notice;
- attention/review: amber;
- blocked/failure: red only for a real stop;
- disabled controls are visibly distinct and keep native semantics;
- long Russian business names wrap instead of overflowing.

## Responsive behavior

At tablet/mobile widths:

- header and hero stack vertically;
- workflow, forms, stats and correction grids become one column;
- primary actions expand to full width;
- tables scroll inside their own container;
- no mandatory horizontal page overflow.

## Safety and accessibility

- system fonts only; no font files;
- visible focus rings;
- reduced-motion support;
- explicit labels and native checkboxes/selects;
- technical hashes, file-system paths and internal identifiers are not promoted into normal UI.
