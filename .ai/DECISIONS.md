# KBSteel ERP - Architectural Decisions

> Non-obvious design choices and their rationale. Check here before making architectural changes.

---

## ADR-001: Dual v1/v2 Architecture

**Decision:** Keep v1 legacy endpoints alongside v2 improved endpoints.

**Why:** v1 is the active production system. v2 adds lot-level traceability, GRN workflow, and immutable audit trails but migration is incomplete. Ripping out v1 would break the live plant.

**Implications:**
- New features should use v2 patterns (StockMovement audit, service layer)
- v1 bug fixes should not introduce v2 dependencies
- Both share the same database — watch for table name conflicts

---

## ADR-002: Immutable Stock Movements (v2)

**Decision:** All inventory changes flow through StockMovement records. Never modify StockLot directly.

**Why:** Steel industry requires full traceability for QA compliance. Every gram must be accountable from receipt to dispatch.

**Implications:**
- Every consume, adjust, transfer creates a StockMovement
- Movements snapshot weight_before and weight_after
- Reversals create a new movement (is_reversed flag), never delete

---

## ADR-003: Weights in KG, Display in Tons

**Decision:** Store all weights in kilograms internally. Convert to tons only for display.

**Why:** KG avoids floating point precision issues for small quantities. Steel is traded in tons but fabricated in kg.

**Implications:**
- Use Decimal type, not float
- `kg_to_tons()` and `tons_to_kg()` utility functions in inventory_service.py
- API responses include both kg and ton values where relevant

---

## ADR-004: Sequential Stage Flow Only

**Decision:** Production stages must follow fabrication → painting → dispatch → completed. No skipping.

**Why:** Physical steel fabrication process cannot skip stages. Paint before fabrication is impossible; dispatch before paint is a quality defect.

**Implications:**
- `STAGE_FLOW` constant in tracking_service.py
- Stage advancement validated server-side
- Frontend Kanban board enforces same order

---

## ADR-005: Auto-Deduction on Fabrication Complete

**Decision:** Automatically deduct raw materials from inventory when fabrication stage completes.

**Why:** Manual deduction was error-prone and delayed. Auto-deduction ensures real-time inventory accuracy.

**Implications:**
- `fabrication_deducted` flag prevents double-deduction (CRITICAL)
- 3-tier matching: direct → manual mapping → fuzzy match on section/code
- If no match found, deduction is skipped (logged, not blocked)

---

## ADR-006: Vanilla JS Frontend (No Framework)

**Decision:** Use vanilla JavaScript with Bootstrap 5 instead of React/Vue/Angular.

**Why:** Simple deployment (static file server), no build step, maintainable by non-frontend specialists at the plant.

**Implications:**
- All 24 HTML pages are self-contained
- Shared logic in config.js (auth, API client) and main.js (UI components)
- Role-based UI via `data-permission` and `data-role` HTML attributes
- No state management library — localStorage for auth, fetch for data

---

## ADR-007: SQLite for Development, PostgreSQL for Production

**Decision:** SQLite in dev mode (auto-create), PostgreSQL required in production.

**Why:** Zero-config development setup. PostgreSQL needed for concurrent users, SELECT FOR UPDATE, and production reliability.

**Implications:**
- `db.py` auto-detects: DATABASE_URL env → PostgreSQL, fallback → SQLite
- Production mode raises RuntimeError if DATABASE_URL missing
- Some v2 features (SELECT FOR UPDATE locking) don't work on SQLite

---

## ADR-008: Service Layer for v2 Business Logic

**Decision:** v2 business logic goes in `services/` directory, not in router files.

**Why:** Router files were growing too large (tracking.py hit 761 lines). Services enable testing and reuse.

**Implications:**
- `inventory_service.py` (801 lines) — the core v2 service
- `tracking_service.py` (398 lines) — stage flow logic
- `production_service.py` (460 lines) — Excel handling
- v1 routers still have inline logic (legacy, not refactored)

---

## ADR-009: Multi-Agent Development (Claude Code + Codex)

**Decision:** Enable delegation from Claude Code to OpenAI Codex CLI for parallel task execution.

**Why:** Complex tasks can be split across agents. Claude Code orchestrates, Codex handles independent subtasks.

**Implications:**
- `codex.md` provides project context to Codex
- `scripts/delegate-to-codex.sh` runs Codex non-interactively
- `.codex-output/` stores results (gitignored)
- Claude Code reviews Codex output before accepting changes

---

## ADR-010: ERPNext-Inspired Workflow Engine

**Decision:** Build a configurable workflow engine instead of hardcoding stage flows.

**Why:** v1 has `STAGE_FLOW` dict, v3 has `DEFAULT_STAGES` — two incompatible pipelines. ERPNext's Workflow doctype pattern allows configurable states, transitions, role-based permissions, and hooks.

**Implications:**
- `services/workflow_engine.py` — dataclass-based state machine
- Hook registry for on_enter/on_exit actions (e.g., material deduction)
- Feature-flagged: `USE_WORKFLOW_ENGINE=false` (default off, opt-in)
- Legacy code preserved in `_advance_stage_legacy()` as fallback

---

## ADR-011: Feature Flags for Gradual Rollout

**Decision:** All major architectural changes behind environment variable feature flags.

**Why:** Production steel plant cannot tolerate downtime. Feature flags enable gradual rollout, A/B testing in staging, and instant rollback.

**Flags:**
- `USE_WORKFLOW_ENGINE` — workflow engine for v1 tracking (default: false)
- `ACCOUNTING_ENABLED` — shadow journal entries from stock movements (default: false)
- `V2_BRIDGE_ENABLED` — dual-write v1 deductions to v2 stock ledger (default: false)

**Implications:**
- Default behavior unchanged without flags
- Staging deployment activates flags for validation
- Production activation after staging validation period

---

## ADR-012: Shadow Accounting (ERPNext GL Entry Pattern)

**Decision:** Auto-create journal entries from stock movements in shadow mode (unposted) before going live.

**Why:** Incorrect accounting entries are worse than no entries. Shadow mode lets admin review before posting. ERPNext creates GL entries for every stock transaction — we adopt the same pattern but with a validation phase.

**Implications:**
- `models_accounting.py` — Account, JournalEntry, JournalEntryLine
- All entries created with `is_posted=False`
- Admin must explicitly post entries after review
- Trial balance available even in shadow mode (for validation)

---

## ADR-013: Stock Valuation on Every Movement

**Decision:** Record valuation data (rate, value change, running balance) on every StockMovement.

**Why:** ERPNext's Stock Ledger Entry tracks both quantity and value. Without per-movement valuation, accounting integration and COGS calculation are impossible.

**Implications:**
- 6 new columns on StockMovement (valuation_rate, stock_value_change, etc.)
- FIFO and weighted-average methods in StockValuationService
- Indian fiscal year format (FY2526) on every movement
- Nullable columns for backward compatibility with existing movements
