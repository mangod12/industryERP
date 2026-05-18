# KBSteel ERP - Full Architecture Context

> Complete reference for all models, endpoints, services, and frontend pages.
> Updated: 2026-05-18

---

## 1. Database Models

### v1 Models (models.py — 324 lines, 15 tables)

| Table | Key Columns | Relationships |
|-------|------------|---------------|
| **users** | id, username, email, hashed_password, role, company, is_active | — |
| **customers** | id, name, project_details, email, phone, is_active, is_deleted, order_status | → production_items |
| **production_items** | id, customer_id, item_code, section, length_mm, qty, weight_per_unit, material_requirements (JSON), checklist (JSON), current_stage, fabrication_deducted, material_deducted | → customer, → stages |
| **stage_tracking** | id, production_item_id, stage, status, started_at, completed_at, updated_by | → production_item |
| **inventory** | id, name, unit, total, used, code, section, category | — |
| **material_usage** | id, customer_id, production_item_id, name, qty, unit, by, applied, ts | — |
| **material_consumption** | id, material_usage_id, inventory_id, qty, ts | — |
| **scrap_records** | id, material_name, weight_kg, length_mm, quantity, reason_code, status, scrap_value | → production_items, → customers |
| **reusable_stock** | id, material_name, length_mm, weight_kg, quantity, quality_grade, is_available | — |
| **material_mappings** | id, excel_name, material_id | → inventory |
| **queries** | id, customer_id, title, message, status, admin_reply | — |
| **instructions** | id, message, created_by | — |
| **notifications** | id, user_id, role, message, level, category, read | — |
| **notification_settings** | id, user_id, per-channel toggles | — |
| **role_notification_settings** | id, role, per-channel toggles | — |
| **excel_uploads** | id, filename, uploaded_by, is_deleted | — |
| **tracking_stage_history** | id, material_id, from_stage, to_stage, changed_by, remarks | — |
| **activity_logs** | id, action, description, user_id, timestamp | — |

### v2 Models (models_v2.py — 738 lines, 12 tables + 2 utility tables)

**Enums:** MaterialType (12 values), WeightUnit (6), MovementType (12), QAStatus (5), DocumentStatus (4)

| Table | Key Columns | Relationships |
|-------|------------|---------------|
| **material_master** | id, code, name, material_type, grade, specification, dimensions, default_unit, reorder_level, hsn_code | → stock_lots |
| **vendors** | id, code, name, gstin, pan, address, contact_person, phone, email | → grns, → stock_lots |
| **storage_locations** | id, code, name, location_type, parent_id, capacity_tons, current_occupancy_tons, is_covered | → children, → stock_lots |
| **stock_lots** | id, lot_number, material_id, heat_number, batch_number, gross/tare/net/current_weight_kg, vendor_id, grn_id, purchase_rate, qa_status, location_id | → material, → vendor, → grn, → movements |
| **stock_movements** | id, movement_number, stock_lot_id, movement_type, weight_change_kg, weight_before/after_kg, reference_type/id, from/to_location_id, reason, created_by, **valuation_rate, stock_value_change, balance_stock_value, balance_qty_kg, posting_date, fiscal_year** | → stock_lot |
| **goods_receipt_notes** | id, grn_number, vendor_id, vehicle_number, gross/tare/net_weight_kg, status, weighbridge_slip_number | → vendor, → line_items, → stock_lots |
| **grn_line_items** | id, grn_id, material_id, heat_number, ordered/received/accepted/rejected_qty, weight_kg, rate, qa_status | → grn, → material |
| **dispatch_notes** | id, dispatch_number, customer_id, vehicle_number, transporter, gross/tare/net_weight_kg, status | → line_items |
| **dispatch_line_items** | id, dispatch_id, stock_lot_id, dispatched_weight_kg, dispatched_qty, rate | → dispatch, → stock_lot |
| **production_items_v2** | id, customer_id, item_code, section, dimensions, ordered/produced_qty, estimated/actual_weight_kg | → stages, → material_consumption |
| **stage_tracking_v2** | id, production_item_id, stage, status, started/completed_at, remarks | → production_item |
| **material_consumption_v2** | id, production_item_id, stock_lot_id, stock_movement_id, consumed_weight_kg, stage | → production_item, → stock_lot |
| **audit_logs** | id, entity_type, entity_id, action, old/new_values (JSON), user_id, ip_address | — |
| **system_config** | id, key, value, description | — |
| **number_sequences** | id, sequence_name, prefix, current_number, year, padding, **format_str** | — |

### v3 Models (models_v3.py — 450 lines, 8 tables)

| Table | Key Columns | Relationships |
|-------|------------|---------------|
| **v3_drawings** | id, drawing_number, revision, title, customer_id, status, total_weight_kg | → assemblies |
| **v3_assemblies** | id, drawing_id, assembly_code, name, quantity | → components |
| **v3_components** | id, assembly_id, component_code, name, material_grade, weight_per_unit_kg | → instances |
| **v3_component_instances** | id, component_id, serial_number, current_stage, stage_updated_at | — |
| **v3_stage_configs** | id, name, sequence, is_mandatory, is_active | — |
| **v3_stage_transitions** | id, instance_id, from_stage, to_stage, transitioned_at, transitioned_by | — |
| **v3_material_reservations** | id, component_id, stock_lot_id, reserved_weight_kg, status | — |
| **v3_drawing_revisions** | id, drawing_id, revision, changes_summary, created_by | — |

### Accounting Models (models_accounting.py — 134 lines, 5 tables)

| Table | Key Columns | Relationships |
|-------|------------|---------------|
| **accounts** | id, code, name, account_type (asset/liability/equity/income/expense), parent_id, is_group, is_active | → children, → journal_lines |
| **fiscal_years** | id, name (FY2526), start_date, end_date, is_active | — |
| **journal_entries** | id, entry_number, posting_date, fiscal_year, reference_type, reference_id, narration, is_posted, total_debit, total_credit, created_by | → lines |
| **journal_entry_lines** | id, journal_entry_id, account_id, debit, credit, cost_center | → journal_entry, → account |
| **cost_centers** | id, code, name, is_active | — |

---

## 2. API Endpoint Registry (~130 total)

### v1 Endpoints (78)

#### Auth & Users (5)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/auth/login` | JWT login |
| POST | `/auth/register` | User registration (Boss/Supervisor) |
| GET | `/users/me` | Current user profile |
| PUT | `/users/me` | Update profile |
| POST | `/users/me/change-password` | Change password |

#### Customers (7)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/customers` | Create customer |
| GET | `/customers` | List customers |
| GET | `/customers/{id}` | Get customer |
| PUT | `/customers/{id}` | Update customer |
| DELETE | `/customers/{id}` | Soft/hard delete |
| POST | `/customers/{id}/items` | Create production item |
| GET | `/customers/{id}/items` | List production items |

#### Tracking - Stage Management (11)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/tracking/customer/{id}` | Customer with stages |
| GET | `/tracking/customers` | List with stage filters |
| PUT | `/tracking/customers/{id}/stage` | Update stage |
| POST | `/tracking/customers/{id}/material-usage` | Record material usage |
| GET | `/tracking/items/search` | Search items |
| GET | `/tracking/items/{id}` | Get item details |
| PUT | `/tracking/items/{id}` | Edit item |
| PUT | `/tracking/items/{id}/checklist` | Update checklist |
| PUT | `/tracking/items/{id}/material-requirements` | Update requirements |
| GET | `/tracking/dashboard/summary` | Dashboard stats |
| GET | `/tracking/all-items` | Paginated all items |

#### Tracking API - List & Export (14)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/tracking` | Active tracking list |
| GET | `/api/tracking/all-items` | Paginated items |
| GET | `/api/tracking/completed` | Completed items |
| GET | `/api/tracking/drawings` | Drawing-wise tracking summary |
| GET | `/api/tracking/export/dispatch` | Export dispatch Excel (→ ExportService) |
| GET | `/api/tracking/export/completed` | Export completed Excel (→ ExportService) |
| GET | `/api/tracking/export/archived` | Export archived Excel (→ ExportService) |
| GET | `/api/tracking/export/company` | Company-wise report (→ ExportService) |
| PUT | `/api/tracking/{id}` | Update tracking |
| POST | `/api/tracking/{id}/move-partial` | Split item quantity |
| POST | `/api/tracking/{id}/archive` | Archive item |
| GET | `/api/tracking/archived` | List archived |
| GET | `/api/tracking/orders/active` | Active orders |
| GET | `/api/tracking/orders/completed` | Completed orders |

#### Inventory (8)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/inventory` | List with filters |
| POST | `/inventory` | Create item |
| PUT | `/inventory/{id}` | Update item |
| DELETE | `/inventory/{id}` | Delete item |
| GET | `/inventory/stats/summary` | Statistics |
| POST | `/inventory/reset-consumed` | Reset consumed |
| POST | `/inventory/reset-stock` | Reset stock |
| GET | `/inventory/dashboard-data` | Dashboard data |

#### Excel Import (7)
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/excel/upload` | Upload Excel/CSV |
| POST | `/excel/import-tracking/{id}` | Import as tracking |
| POST | `/excel/preview-import/{id}` | Preview import |
| GET | `/excel/template` | Download template |
| DELETE | `/excel/{id}` | Delete upload |
| POST | `/excel/upload-stage/{stage}` | Stage-specific upload |
| POST | `/excel/preview-stage/{stage}` | Stage preview |

#### Scrap & Reusable (15) — business logic in ScrapService
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/scrap/records` | List scrap |
| POST | `/scrap/records` | Create scrap |
| POST | `/scrap/upload-csv` | Bulk CSV upload |
| PUT | `/scrap/records/{id}/status` | Update status |
| PUT | `/scrap/records/{id}/return-to-inventory` | Return to inventory |
| PUT | `/scrap/records/{id}/move-to-reusable` | Move to reusable |
| DELETE | `/scrap/records/{id}` | Delete scrap |
| GET | `/scrap/reusable` | List reusable |
| GET | `/scrap/reusable/find-match` | Find matching |
| POST | `/scrap/reusable` | Add reusable |
| PUT | `/scrap/reusable/{id}/use` | Use in item |
| PUT | `/scrap/reusable/{id}/return-to-inventory` | Return |
| PUT | `/scrap/reusable/{id}/mark-scrap` | Mark as scrap |
| GET | `/scrap/analytics` | Loss analytics |
| GET | `/scrap/summary` | Summary report |

#### Dashboard (2)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/dashboard/summary` | Legacy dashboard stats |
| GET | `/dashboard/enhanced-summary` | **NEW** — 6 number cards (stock value, pending GRNs, dispatches, production %, scrap rate, low stock) + recent activity |

#### Other v1 (5)
| Method | Path | Purpose |
|--------|------|---------|
| POST/GET/PUT/DELETE | `/instructions` | Boss instructions CRUD |
| POST/GET | `/queries` | Support tickets |
| GET/PUT | `/notifications` | Notification system |
| GET/POST | `/mappings` | Material mappings |

### v2 Endpoints (52)

#### Inventory v2 — `/api/v2/inventory` (13)
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/materials` | List materials |
| POST | `/materials` | Create material |
| GET | `/lots` | List stock lots |
| GET | `/lots/{id}` | Lot detail |
| POST | `/consume` | Consume from lot |
| POST | `/adjust` | Adjust weight |
| POST | `/transfer-location` | Transfer lot |
| GET | `/summary` | Stock summary |
| GET | `/aging-report` | FIFO aging |
| GET | `/movements/{id}` | Audit trail |
| GET | `/alerts/low-stock` | Low stock alerts |
| POST | `/reconcile` | Reconciliation |
| GET | `/reconciliation` | **NEW** — v1/v2 inventory bridge reconciliation report |

#### GRN — `/api/v2/grn` (10) — uses workflow engine for status transitions
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/vendors` | List vendors |
| POST | `/vendors` | Create vendor |
| GET | `/` | List GRNs |
| POST | `/` | Create GRN |
| POST | `/{id}/line-items` | Add line item |
| POST | `/{id}/weighment` | Weighbridge data |
| POST | `/{id}/submit` | Submit for QA (→ WorkflowEngine) |
| POST | `/{id}/qa-inspection` | QA decision |
| POST | `/{id}/approve` | Approve → create lots (→ WorkflowEngine) |
| POST | `/{id}/cancel` | Cancel GRN (→ WorkflowEngine) |

#### Dispatch — `/api/v2/dispatch` (9) — uses workflow engine for status transitions
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | List dispatches |
| POST | `/` | Create dispatch |
| POST | `/{id}/line-items` | Pick stock lot |
| POST | `/{id}/auto-pick` | FIFO auto-pick |
| POST | `/{id}/weighment` | Weighbridge data |
| POST | `/{id}/submit` | Submit for approval (→ WorkflowEngine) |
| POST | `/{id}/approve` | Approve → deduct stock (→ WorkflowEngine) |
| POST | `/{id}/cancel` | **NEW** — Cancel dispatch (→ WorkflowEngine) |
| DELETE | `/{id}/line-items/{item_id}` | Remove line item |

#### Print Formats — `/api/v2/print` (1) **NEW**
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/{document_type}/{document_id}` | Generate GRN/dispatch/challan as HTML or PDF (`?format=html\|pdf`) |

#### Reports — `/api/v2/reports` (3) **NEW**
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | List available reports (8 types) |
| GET | `/{report_name}` | Run report with query param filters |
| GET | `/{report_name}/export` | Export report as Excel |

**Available reports:** stock-balance, stock-ledger, stock-aging, material-consumption, scrap-analysis, production-progress, grn-register, dispatch-register

#### Settings — `/api/v2/settings` (7) **NEW**
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/company` | Company profile (name, GSTIN, address) |
| PUT | `/company` | Update company profile (Boss only) |
| GET | `/naming-series` | List number sequences with formats |
| PUT | `/naming-series/{name}` | Update naming series format (Boss only) |
| GET | `/workflows` | List v3 stage configs |
| GET | `/system` | List all system_config key-values |
| PUT | `/system/{key}` | Update system config (Boss only) |

---

## 3. Service Layer

| Service | File | Lines | Key Functions |
|---------|------|-------|---------------|
| **InventoryService** | services/inventory_service.py | 867 | StockLotService (create_lot_from_grn, consume_from_lot), InventoryQueryService (FIFO/LIFO, aging, alerts), GRNService (full workflow), weight conversion, get_next_sequence (enhanced with format tokens + Indian FY) |
| **TrackingService** | services/tracking_service.py | 716 | STAGE_FLOW + WorkflowEngine integration (feature-flagged), advance_stage (legacy + engine paths), _deduct_materials_for_fabrication (with v2 bridge), split_item, toggle_checklist, compute_customer_stage, get_dashboard_summary |
| **ProductionService** | services/production_service.py | 491 | 90+ Excel column aliases, read_file_to_dataframe, 3-tier fuzzy matching, preview_production_excel |
| **CustomerService** | services/customer_service.py | 107 | Basic CRUD helpers |
| **WorkflowEngine** | services/workflow_engine.py | 617 | **NEW** — Configurable state machine: WorkflowDefinition, WorkflowState, WorkflowTransition, hook registry. Built-in workflows: production_v1, production_v3, document (GRN/dispatch). transition_document() convenience function |
| **StockValuationService** | services/stock_valuation_service.py | 273 | **NEW** — FIFO/weighted-avg valuation, record_valuation_on_movement, get_fiscal_year, get_stock_value_summary |
| **AccountingService** | services/accounting_service.py | 320 | **NEW** — Double-entry ledger, seed_default_accounts (12 accounts), create_journal_entry, create_entry_for_stock_movement, post_entries, get_trial_balance. Feature-flagged ACCOUNTING_ENABLED |
| **PrintService** | services/print_service.py | 301 | **NEW** — Jinja2 + xhtml2pdf, render_html/render_pdf, generate_grn_document, generate_dispatch_document, generate_delivery_challan, get_company_info |
| **ReportService** | services/report_service.py | 703 | **NEW** — 8 predefined reports (stock balance/ledger/aging, consumption, scrap, production, GRN/dispatch register), export_to_excel, REPORT_REGISTRY |
| **ScrapService** | services/scrap_service.py | 658 | **NEW** — Extracted from scrap.py: ScrapService, ReusableStockService, ScrapAnalyticsService. DEFAULT_SCRAP_RATE_PER_KG constant |
| **ExportService** | services/export_service.py | 117 | **NEW** — Extracted from tracking_api.py: export_dispatch_excel, export_completed_excel, export_archived_excel, export_company_report |
| **InventoryBridgeService** | services/inventory_bridge.py | 365 | **NEW** — v1/v2 bridge: find_matching_v2_lot, bridge_deduction (creates v2 StockMovement from v1 deduction), get_reconciliation_report. Feature-flagged V2_BRIDGE_ENABLED |
| **DrawingService** | services/drawing_service.py | 545 | v3 drawing CRUD, revision management, status transitions |
| **ComponentTrackingService** | services/component_tracking_service.py | 733 | v3 component instance stage tracking |

---

## 4. Security Architecture

| Component | Detail |
|-----------|--------|
| **Secret Key** | KUMAR_SECRET_KEY env var (min 32 chars, required in prod) |
| **JWT** | HS256, 24hr access token, 7-day refresh |
| **Passwords** | bcrypt hash, policy: 8-128 chars, mixed case, digit, special |
| **RBAC** | 25 fine-grained permissions across 6 roles |
| **Rate Limiting** | In-memory, 5 attempts per 5 min |
| **Audit** | SecurityAuditLog for login attempts and sensitive actions |
| **Input** | sanitize_input() removes null bytes, validate_email() regex |
| **Dual Dependencies** | Both `security.py` and `deps.py` define get_db/get_current_user — routers import from either |

---

## 5. Frontend Pages (25)

| Page | Purpose | Key API Calls |
|------|---------|---------------|
| login.html | Authentication | POST /auth/login |
| index.html | Dashboard | GET /dashboard/summary, /dashboard/enhanced-summary |
| register.html | User creation | POST /auth/register |
| customers.html | Customer list | GET /customers, POST /excel/upload |
| customer_add.html | Add customer | POST /customers |
| customer_edit.html | Edit customer | PUT /customers/{id} |
| customer_details.html | Customer detail | GET /customers/{id} |
| raw_material.html | Inventory CRUD | GET/POST/PUT/DELETE /inventory |
| materials.html | Materials master | GET /api/v2/inventory/materials |
| scrap.html | Scrap tracking | GET/POST /scrap/records |
| reusable.html | Reusable stock | GET/POST /scrap/reusable |
| grn.html | Goods receipt | GET/POST /api/v2/grn |
| dispatch.html | Dispatch notes | GET/POST /api/v2/dispatch |
| tracking_v2.html | Kanban board | GET /tracking/all-items, /api/tracking/drawings |
| instructions.html | Boss instructions | GET/POST /instructions |
| queries.html | Support tickets | GET/POST /queries |
| settings.html | Settings hub | Links to sub-pages |
| **system-settings.html** | **NEW** — System admin | GET/PUT /api/v2/settings/* (company, naming, workflows, config) |
| account-settings.html | Account mgmt | PUT /users/me |
| notification-settings.html | Notif prefs | GET/PUT /notifications/settings |
| stock.html | Stock overview | GET /api/v2/inventory/summary |
| drawings.html | v3 drawings | GET /api/v3/drawings |

---

## 6. Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| KUMAR_SECRET_KEY | prod | — | JWT signing key (min 32 chars) |
| ENVIRONMENT | no | development | prod vs dev mode |
| DATABASE_URL | prod | sqlite:///./data/kbsteel_dev.db | Database connection |
| CORS_ORIGINS | no | localhost | Comma-separated origins |
| TOKEN_EXPIRE_MINUTES | no | 1440 | JWT access token expiry |
| REFRESH_TOKEN_EXPIRE_DAYS | no | 7 | Refresh token expiry |
| **USE_WORKFLOW_ENGINE** | no | false | **NEW** — Enable configurable workflow engine for v1 stage tracking |
| **ACCOUNTING_ENABLED** | no | false | **NEW** — Enable shadow accounting journal entries from stock movements |
| **V2_BRIDGE_ENABLED** | no | false | **NEW** — Enable v1→v2 inventory bridge (dual-write deductions to v2 stock ledger) |

---

## 7. Migration System

**Alembic** manages all schema changes. Hand-rolled `_run_migrations()` in db.py is deprecated.

| Migration | Description |
|-----------|-------------|
| `86fbcc9926b2` | Baseline — all 40+ existing tables (v1/v2/v3) |
| `f9175aa2e862` | Add valuation columns to stock_movements (6 columns) |
| `a3c1d7f8b920` | Add format_str to number_sequences |
| `8cfee71f655e` | Add accounting tables (5 tables) |

**Commands:**
- New migration: `alembic revision --autogenerate -m "description"`
- Apply: `alembic upgrade head`
- Existing prod DB: `alembic stamp head` (one-time baseline)

---

## 8. Testing & CI

**492 tests**, 0 lint errors, 4-job CI pipeline.

| Test File | Tests | Covers |
|-----------|-------|--------|
| test_tracking_service.py | 51 | Stage flow, deduction, split, checklist, workflow engine integration |
| test_inventory_service.py | 46 | Stock lots, FIFO, GRN, reconciliation, weights |
| test_production_service.py | 34 | Column mapping, fuzzy match, preview |
| test_scrap_service.py | 54 | Scrap CRUD, reusable stock, analytics, CSV import |
| test_workflow_engine.py | 64 | State machine, transitions, hooks, built-in workflows |
| test_document_workflow.py | 27 | GRN/dispatch doc workflows, role enforcement |
| test_stock_valuation.py | 25 | FIFO/weighted-avg, fiscal year, balance tracking |
| test_naming_series.py | 34 | Format tokens, FY support, SQLite compatibility |
| test_accounting_service.py | 20 | Journal entries, trial balance, movement mapping |
| test_print_service.py | 21 | HTML/PDF rendering, data gathering |
| test_report_service.py | 41 | All 8 reports, filters, Excel export |
| test_dashboard_settings.py | 30 | Enhanced dashboard, settings CRUD, role enforcement |
| test_inventory_bridge.py | 22 | v1/v2 bridge, reconciliation, feature flag |
| test_smoke.py | 11 | Infrastructure validation |
| test_v3_drawings.py | 14 | v3 drawing lifecycle |

**CI Pipeline** (`.github/workflows/ci.yml`):
1. **lint** — ruff check + format check
2. **test** — pytest with 80% coverage gate
3. **type-check** — mypy on services/ (advisory)
4. **docker-build** — Docker image build + container start verification

---

## 9. Active Concerns

1. ~~No tests~~ → **492 tests** (RESOLVED)
2. ~~No CI/CD~~ → **4-job pipeline** (RESOLVED)
3. ~~Alembic incomplete~~ → **4 migrations** (RESOLVED)
4. ~~scrap.py 745 lines~~ → **386 lines** + ScrapService (RESOLVED)
5. **excel.py (441 lines)** — 90+ column aliases, fragile matching (UNCHANGED)
6. ~~tracking.py 761 lines~~ → **618 lines** + ExportService (IMPROVED)
7. ~~v1/v2 Base conflict~~ → **unified Base, single create_all** (RESOLVED)
8. ~~Hardcoded scrap loss~~ → **DEFAULT_SCRAP_RATE_PER_KG constant** (RESOLVED)
9. ~~SELECT FOR UPDATE on SQLite~~ → **optimistic locking** (RESOLVED)
10. **Debug prints** — inventory.py:29 still present
11. **TODO** — inventory.py:223 "implement proper audit logging"
12. **tracking_api.py (524 lines)** — still above 400-line target
13. **inventory_service.py (867 lines)** — exceeds 800-line limit, consider splitting
14. **Dual deps.py/security.py** — two modules defining same dependencies, conftest overrides both
