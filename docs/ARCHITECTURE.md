# Architecture Light

STATUS: `DRAFT / NO_LIVE_WRITE`

```text
UI
 ↓
Application / Workflow
 ↓
Business Core
 ↓
Adapters
 ├─ Excel
 ├─ References
 └─ ADO / 1C
 ↓
Audit / Runs / Support
```

## Principles

- Business Core не знает о кнопках UI, ADO connection objects и абсолютных filesystem paths.
- После validation exact input фиксируется в immutable RUN-local snapshot.
- Один business action — максимум один RUN/operation (single-flight/idempotent).
- Input определяется по структуре/schema, а не filename.
- UI/API получает business-safe public DTO по allowlist.
- Downstream stage получает exact handoff, а не ищет `latest file`.

## Planned delivery stages

1. Excel → validation → transform → preview.
2. Validation/error UX stabilization.
3. ADO read-only / DRY RUN.
4. TEST write with explicit owner gate, transaction and read-back verification.
5. Deterministic packaging/release.
6. Production gate отдельно.
