# Architecture Decision Records (ADR)

> Track significant design decisions and their rationale.

## Format
```
### ADR-NNN: Title
- **Status:** proposed | accepted | deprecated | superseded
- **Date:** YYYY-MM-DD
- **Context:** why this decision was needed
- **Decision:** what was decided
- **Consequences:** tradeoffs and impacts
```

---

### ADR-001: Dual v1/v2 Model Architecture
- **Status:** accepted (pre-existing)
- **Date:** pre-2026-03-28
- **Context:** v1 models used Float for weights and lacked lot-level traceability. Steel operations need Decimal precision and full audit trails.
- **Decision:** Added v2 models (models_v2.py) alongside v1 rather than migrating in-place. Both share the same SQLAlchemy Base and database.
- **Consequences:** Increased complexity, potential table name conflicts, migration script needed. But zero-downtime for existing users.

### ADR-002: SQLite for Development
- **Status:** accepted (pre-existing)
- **Date:** pre-2026-03-28
- **Context:** Need simple setup for single-user development.
- **Decision:** Use SQLite with fallback to in-memory if data dir creation fails.
- **Consequences:** No SELECT FOR UPDATE support (race conditions possible), no concurrent writes, limited to ~1GB practical size. Must switch to PostgreSQL for production multi-user.

### ADR-003: Vanilla JS Frontend (No Framework)
- **Status:** accepted (pre-existing)
- **Date:** pre-2026-03-28
- **Context:** Quick prototyping, minimal build tooling.
- **Decision:** Static HTML + Bootstrap 5 + vanilla fetch() calls.
- **Consequences:** Fast to iterate, no build step, but code duplication across 22 HTML files, no component reuse, manual DOM manipulation.
