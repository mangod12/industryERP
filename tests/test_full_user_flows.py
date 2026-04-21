"""
Full User Flow Tests — simulates a real user interacting with every page and input stream.
Runs against the LIVE server at http://127.0.0.1:8000.

Tests cover:
1. Login page
2. Dashboard page
3. Customer management (create, list, edit, delete)
4. Inventory (create, list, update, delete)
5. Excel upload (template download, upload)
6. Tracking (list, update stages, search)
7. Drawings v3 (full lifecycle: create → add assemblies → add components → release → advance → kanban → material usage)
8. Scrap management
9. Queries (create, reply, close)
10. Instructions (create, list, edit, delete)
11. Notifications
12. User settings
13. Frontend HTML pages load check
"""

import requests
import json
import time
import os

BASE = "http://127.0.0.1:8000"
SESSION = requests.Session()
TOKEN = None
HEADERS = {}

# Track results
results = []
RUN_ID = str(int(time.time()))[-6:]  # Unique suffix per run

def log(test_name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append({"test": test_name, "status": status, "detail": detail})
    icon = "OK" if passed else "FAIL"
    print(f"  {icon} {test_name}" + (f" — {detail}" if detail and not passed else ""))


def assert_ok(resp, test_name, expected_codes=(200, 201)):
    if resp.status_code in expected_codes:
        log(test_name, True)
        return True
    else:
        log(test_name, False, f"HTTP {resp.status_code}: {resp.text[:200]}")
        return False


# ============================================================================
# 1. LOGIN PAGE
# ============================================================================
print("\n=== 1. LOGIN ===")

# Bad credentials
r = SESSION.post(f"{BASE}/auth/login", json={"username": "wrong", "password": "wrong"})
log("Login with bad creds returns 401", r.status_code == 401)

# Missing/empty fields
r = SESSION.post(f"{BASE}/auth/login", json={"username": "", "password": ""})
log("Login with empty creds returns error", r.status_code in (400, 401, 422))

# Good login
r = SESSION.post(f"{BASE}/auth/login", json={"username": "boss", "password": "Boss1234!"})
if assert_ok(r, "Login with valid creds"):
    data = r.json()
    TOKEN = data["access_token"]
    HEADERS = {"Authorization": f"Bearer {TOKEN}"}
    log("Token received", bool(TOKEN))
    log("Role is Boss", data.get("role") == "Boss")

# ============================================================================
# 2. DASHBOARD
# ============================================================================
print("\n=== 2. DASHBOARD ===")

r = SESSION.get(f"{BASE}/dashboard/summary", headers=HEADERS)
assert_ok(r, "Dashboard summary loads")

r = SESSION.get(f"{BASE}/inventory/dashboard-data", headers=HEADERS)
assert_ok(r, "Inventory dashboard data loads")

# ============================================================================
# 3. CUSTOMER MANAGEMENT
# ============================================================================
print("\n=== 3. CUSTOMERS ===")

# Create customer
r = SESSION.post(f"{BASE}/customers", headers=HEADERS, json={
    "name": "Acme Steel Works",
    "project_details": "Factory extension project"
})
if assert_ok(r, "Create customer"):
    cust_id = r.json()["id"]
    log("Customer has ID", cust_id > 0)

# List customers
r = SESSION.get(f"{BASE}/customers", headers=HEADERS)
if assert_ok(r, "List customers"):
    log("At least 1 customer", len(r.json()) >= 1)

# Get single customer
r = SESSION.get(f"{BASE}/customers/{cust_id}", headers=HEADERS)
assert_ok(r, "Get single customer")

# Update customer
r = SESSION.put(f"{BASE}/customers/{cust_id}", headers=HEADERS, json={
    "name": "Acme Steel Works Pvt Ltd",
    "project_details": "Updated project details"
})
assert_ok(r, "Update customer")

# Create another customer for testing
r = SESSION.post(f"{BASE}/customers", headers=HEADERS, json={
    "name": "Beta Fabricators",
    "project_details": "Bridge project"
})
cust2_id = r.json()["id"] if r.status_code in (200, 201) else None

# ============================================================================
# 4. INVENTORY
# ============================================================================
print("\n=== 4. INVENTORY ===")

# Create inventory items (idempotent — skip if exists)
inv_id = None
for item_data in [
    {"name": "UB203X133X25", "unit": "kg", "total": 5000, "used": 0, "code": "UB203", "section": "UB203X133X25", "category": "Beam"},
    {"name": "50x50x5 SHS", "unit": "kg", "total": 2000, "used": 0, "code": "SHS50", "section": "50x50x5", "category": "Hollow Section"},
    {"name": "6mm Plate", "unit": "kg", "total": 3000, "used": 0, "code": "PL6", "section": "6mm plate", "category": "Plate"},
]:
    r = SESSION.post(f"{BASE}/inventory", headers=HEADERS, json=item_data)
    if r.status_code in (200, 201):
        log(f"Create inventory: {item_data['name']}", True)
        if item_data["name"] == "UB203X133X25":
            inv_id = r.json()["id"]
    elif r.status_code == 400 and "already exists" in r.text:
        log(f"Inventory exists: {item_data['name']} (OK)", True)
    else:
        log(f"Create inventory: {item_data['name']}", False, f"HTTP {r.status_code}")

# Find inv_id for UB203 if not set
if not inv_id:
    r = SESSION.get(f"{BASE}/inventory", headers=HEADERS)
    if r.status_code == 200:
        for item in r.json():
            if "UB203" in (item.get("name") or ""):
                inv_id = item["id"]
                break

# List inventory
r = SESSION.get(f"{BASE}/inventory", headers=HEADERS)
if assert_ok(r, "List inventory"):
    log("At least 3 items", len(r.json()) >= 3)

# Update inventory
r = SESSION.put(f"{BASE}/inventory/{inv_id}", headers=HEADERS, json={
    "name": "UB203X133X25", "unit": "kg", "total": 6000, "used": 100,
    "code": "UB203", "section": "UB203X133X25", "category": "Beam"
})
assert_ok(r, "Update inventory item")

# Inventory stats
r = SESSION.get(f"{BASE}/inventory/stats/summary", headers=HEADERS)
assert_ok(r, "Inventory stats/summary")

# ============================================================================
# 5. EXCEL TEMPLATE
# ============================================================================
print("\n=== 5. EXCEL ===")

r = SESSION.get(f"{BASE}/excel/template", headers=HEADERS)
assert_ok(r, "Download Excel template")

# ============================================================================
# 6. TRACKING (v1)
# ============================================================================
print("\n=== 6. TRACKING (v1) ===")

r = SESSION.get(f"{BASE}/api/tracking", headers=HEADERS)
assert_ok(r, "List tracking items")

r = SESSION.get(f"{BASE}/api/tracking/all-items?page=1&page_size=10", headers=HEADERS)
assert_ok(r, "All tracking items paginated")

r = SESSION.get(f"{BASE}/tracking/dashboard/summary", headers=HEADERS)
assert_ok(r, "Tracking dashboard summary")

r = SESSION.get(f"{BASE}/api/tracking/orders/active", headers=HEADERS)
assert_ok(r, "Active orders list")

r = SESSION.get(f"{BASE}/api/tracking/orders/completed", headers=HEADERS)
assert_ok(r, "Completed orders list")

# ============================================================================
# 7. DRAWINGS v3 — FULL LIFECYCLE
# ============================================================================
print("\n=== 7. DRAWINGS v3 ===")

# Create drawing
r = SESSION.post(f"{BASE}/api/v3/drawings/", headers=HEADERS, json={
    "drawing_number": f"DWG-TEST-{RUN_ID}",
    "title": "Staircase Handrail Assembly",
    "customer_id": cust_id,
    "project_ref": f"PRJ-ACME-{RUN_ID}",
    "notes": "Test drawing for user flow"
})
if assert_ok(r, "Create drawing"):
    dwg = r.json()
    dwg_id = dwg["id"]
    log("Drawing status is draft", dwg["status"] == "draft")
    log("Drawing revision is A", dwg["revision"] == "A")

# List drawings
r = SESSION.get(f"{BASE}/api/v3/drawings/", headers=HEADERS)
if assert_ok(r, "List drawings"):
    log("At least 1 drawing", len(r.json()) >= 1)

# Filter by customer
r = SESSION.get(f"{BASE}/api/v3/drawings/?customer_id={cust_id}", headers=HEADERS)
assert_ok(r, "List drawings filtered by customer")

# Filter by status
r = SESSION.get(f"{BASE}/api/v3/drawings/?status=draft", headers=HEADERS)
assert_ok(r, "List drawings filtered by status")

# Add assembly
r = SESSION.post(f"{BASE}/api/v3/drawings/{dwg_id}/assemblies", headers=HEADERS, json={
    "mark_number": "HR-A1",
    "description": "Handrail main frame — left side",
    "quantity_required": 2
})
if assert_ok(r, "Add assembly"):
    asm_id = r.json()["id"]

# Add second assembly
r = SESSION.post(f"{BASE}/api/v3/drawings/{dwg_id}/assemblies", headers=HEADERS, json={
    "mark_number": "HR-A2",
    "description": "End post assembly",
    "quantity_required": 4
})
if assert_ok(r, "Add second assembly"):
    asm2_id = r.json()["id"]

# Add components to assembly 1
r = SESSION.post(f"{BASE}/api/v3/drawings/assemblies/{asm_id}/components", headers=HEADERS, json={
    "piece_mark": "P1", "profile_section": "UB203X133X25", "grade": "S275",
    "length_mm": 3200, "quantity_per_assembly": 1, "weight_each_kg": 80.0,
    "inventory_id": inv_id
})
if assert_ok(r, "Add component P1 (beam)"):
    comp1_id = r.json()["id"]

r = SESSION.post(f"{BASE}/api/v3/drawings/assemblies/{asm_id}/components", headers=HEADERS, json={
    "piece_mark": "P2", "profile_section": "50x50x5 SHS", "grade": "S275",
    "length_mm": 1100, "quantity_per_assembly": 3, "weight_each_kg": 8.5
})
assert_ok(r, "Add component P2 (posts)")

r = SESSION.post(f"{BASE}/api/v3/drawings/assemblies/{asm_id}/components", headers=HEADERS, json={
    "piece_mark": "P3", "profile_section": "6mm Base Plate",
    "length_mm": 300, "width_mm": 300, "thickness_mm": 6,
    "quantity_per_assembly": 2, "weight_each_kg": 4.2
})
assert_ok(r, "Add component P3 (base plate)")

# Add component to assembly 2
r = SESSION.post(f"{BASE}/api/v3/drawings/assemblies/{asm2_id}/components", headers=HEADERS, json={
    "piece_mark": "EP1", "profile_section": "75x75x6 Angle", "grade": "S275",
    "length_mm": 1000, "quantity_per_assembly": 1, "weight_each_kg": 6.8
})
assert_ok(r, "Add component EP1 to assembly 2")

# Get drawing detail (before release)
r = SESSION.get(f"{BASE}/api/v3/drawings/{dwg_id}", headers=HEADERS)
if assert_ok(r, "Get drawing detail (pre-release)"):
    log("Status still draft", r.json()["status"] == "draft")

# Try to release — should work
r = SESSION.post(f"{BASE}/api/v3/drawings/{dwg_id}/release", headers=HEADERS)
if assert_ok(r, "Release drawing"):
    data = r.json()
    instance_count = data.get("instance_count", 0)
    # Assembly 1: qty=2 * (1+3+2) = 12 instances
    # Assembly 2: qty=4 * 1 = 4 instances
    # Total = 16
    log(f"Instance count is 16 (got {instance_count})", instance_count == 16)
    log("Status is released", data["status"] == "released")

# Try double-release — should fail
r = SESSION.post(f"{BASE}/api/v3/drawings/{dwg_id}/release", headers=HEADERS)
log("Double-release blocked", r.status_code in (400, 404))

# Get progress
r = SESSION.get(f"{BASE}/api/v3/drawings/{dwg_id}/progress", headers=HEADERS)
if assert_ok(r, "Get drawing progress"):
    prog = r.json()
    log(f"Total instances = {prog['total_instances']}", prog["total_instances"] == 16)
    log("All at cutting stage", prog["stages"].get("cutting", 0) == 16)
    log("0% complete", prog["pct_complete"] == 0.0)

# Get material usage
r = SESSION.get(f"{BASE}/api/v3/drawings/{dwg_id}/material-usage", headers=HEADERS)
if assert_ok(r, "Get material usage"):
    mu = r.json()
    log("BOM weight > 0", mu["total_bom_weight_kg"] > 0)
    log("0% consumed", mu["consumption_pct"] == 0.0)
    log("2 assemblies in report", len(mu["assemblies"]) == 2)
    # Check P1 has inventory link
    a1 = next(a for a in mu["assemblies"] if a["mark_number"] == "HR-A1")
    p1 = next(c for c in a1["components"] if c["piece_mark"] == "P1")
    log(f"P1 required: {p1['total_required_kg']}kg", p1["total_required_kg"] == 160.0)

# Get kanban
r = SESSION.get(f"{BASE}/api/v3/drawings/kanban?drawing_id={dwg_id}", headers=HEADERS)
if assert_ok(r, "Get kanban board"):
    kanban = r.json()
    log("Kanban has columns", len(kanban["columns"]) > 0)
    cutting_col = next((c for c in kanban["columns"] if c["stage_name"] == "cutting"), None)
    log(f"Cutting column has 16 instances", cutting_col and cutting_col["count"] == 16)

# --- ADVANCE STAGE FLOW ---
# Find instance IDs from kanban
instance_ids = []
if cutting_col:
    instance_ids = [i["id"] for i in cutting_col["instances"][:4]]

if len(instance_ids) >= 4:
    # Start first instance
    iid = instance_ids[0]
    r = SESSION.post(f"{BASE}/api/v3/drawings/instances/{iid}/start", headers=HEADERS)
    assert_ok(r, f"Start instance #{iid}")

    # Advance to drilling
    r = SESSION.post(f"{BASE}/api/v3/drawings/instances/{iid}/advance", headers=HEADERS, json={
        "component_instance_id": iid, "remarks": "Cutting complete"
    })
    if assert_ok(r, f"Advance instance #{iid} cutting→drilling"):
        adv = r.json()
        log("From cutting", adv.get("from_stage") == "cutting")

    # Advance second instance
    iid2 = instance_ids[1]
    r = SESSION.post(f"{BASE}/api/v3/drawings/instances/{iid2}/start", headers=HEADERS)
    r = SESSION.post(f"{BASE}/api/v3/drawings/instances/{iid2}/advance", headers=HEADERS, json={
        "component_instance_id": iid2, "remarks": "Cut done"
    })
    assert_ok(r, f"Advance instance #{iid2}")

    # Hold an instance
    iid3 = instance_ids[2]
    r = SESSION.post(f"{BASE}/api/v3/drawings/instances/{iid3}/start", headers=HEADERS)
    r = SESSION.post(f"{BASE}/api/v3/drawings/instances/{iid3}/hold", headers=HEADERS, json={
        "reason": "Material defect found — waiting for QA"
    })
    assert_ok(r, f"Hold instance #{iid3}")

    # Hold without reason — should fail
    r = SESSION.post(f"{BASE}/api/v3/drawings/instances/{iid3}/hold", headers=HEADERS, json={
        "reason": ""
    })
    log("Hold without reason fails", r.status_code in (400, 422))

    # Scrap an instance
    iid4 = instance_ids[3]
    r = SESSION.post(f"{BASE}/api/v3/drawings/instances/{iid4}/start", headers=HEADERS)
    r = SESSION.post(f"{BASE}/api/v3/drawings/instances/{iid4}/scrap", headers=HEADERS, json={
        "reason": "Cutting error — piece too short"
    })
    assert_ok(r, f"Scrap instance #{iid4}")

    # Scrap without reason — should fail
    r = SESSION.post(f"{BASE}/api/v3/drawings/instances/{iid4}/scrap", headers=HEADERS, json={
        "reason": ""
    })
    log("Scrap without reason fails", r.status_code in (400, 422))

    # Batch advance
    batch_ids = instance_ids[0:2]  # advance the two that are in drilling
    r = SESSION.post(f"{BASE}/api/v3/drawings/instances/batch-advance", headers=HEADERS, json={
        "instance_ids": batch_ids,
        "target_stage": "fitting",
        "remarks": "Drilling done, moving to fitting",
        "station": "Drill Bay 1"
    })
    assert_ok(r, "Batch advance 2 instances drilling→fitting")

    # Check progress now
    r = SESSION.get(f"{BASE}/api/v3/drawings/{dwg_id}/progress", headers=HEADERS)
    if assert_ok(r, "Progress after stage advances"):
        prog = r.json()
        log(f"Completed: {prog['completed_instances']}", True)
        log(f"Stages: {prog['stages']}", True)

    # Reserve materials
    r = SESSION.post(f"{BASE}/api/v3/drawings/{dwg_id}/reserve-materials", headers=HEADERS, json={
        "drawing_id": dwg_id
    })
    # May partially succeed (only P1 has inventory_id linked)
    log(f"Reserve materials: HTTP {r.status_code}", r.status_code in (200, 400))

    # Advance instance through multiple stages rapidly
    r = SESSION.post(f"{BASE}/api/v3/drawings/instances/{iid}/start", headers=HEADERS)
    r = SESSION.post(f"{BASE}/api/v3/drawings/instances/{iid}/advance", headers=HEADERS, json={
        "component_instance_id": iid, "remarks": "Fitting done"
    })
    assert_ok(r, f"Advance #{iid} fitting→welding")
    r = SESSION.post(f"{BASE}/api/v3/drawings/instances/{iid}/start", headers=HEADERS)
    r = SESSION.post(f"{BASE}/api/v3/drawings/instances/{iid}/advance", headers=HEADERS, json={
        "component_instance_id": iid, "remarks": "Welding done"
    })
    assert_ok(r, f"Advance #{iid} welding→painting")

# Try to skip stages (should fail)
if instance_ids:
    r = SESSION.post(f"{BASE}/api/v3/drawings/instances/{instance_ids[0]}/advance", headers=HEADERS, json={
        "component_instance_id": instance_ids[0], "target_stage": "completed"
    })
    log("Skip to completed blocked", r.status_code == 400)

# Advance nonexistent instance
r = SESSION.post(f"{BASE}/api/v3/drawings/instances/99999/advance", headers=HEADERS, json={
    "component_instance_id": 99999
})
log("Advance nonexistent instance: 400/404", r.status_code in (400, 404))


# ============================================================================
# 8. SCRAP MANAGEMENT
# ============================================================================
print("\n=== 8. SCRAP ===")

r = SESSION.get(f"{BASE}/scrap/records", headers=HEADERS)
assert_ok(r, "List scrap records")

r = SESSION.post(f"{BASE}/scrap/records", headers=HEADERS, json={
    "material_name": "UB203X133X25",
    "weight_kg": 15.5,
    "quantity": 1,
    "reason_code": "cutting_error",
    "notes": "Short cut from staircase project"
})
if assert_ok(r, "Create scrap record"):
    scrap_id = r.json().get("id")

r = SESSION.get(f"{BASE}/scrap/reusable", headers=HEADERS)
assert_ok(r, "List reusable stock")

r = SESSION.get(f"{BASE}/scrap/analytics", headers=HEADERS)
assert_ok(r, "Scrap analytics")

r = SESSION.get(f"{BASE}/scrap/summary", headers=HEADERS)
assert_ok(r, "Scrap summary")


# ============================================================================
# 9. QUERIES
# ============================================================================
print("\n=== 9. QUERIES ===")

r = SESSION.post(f"{BASE}/queries/", headers=HEADERS, json={
    "title": "Material shortage",
    "message": "Running low on UB203 for staircase project"
})
if assert_ok(r, "Create query"):
    query_id = r.json()["id"]

r = SESSION.get(f"{BASE}/queries/me", headers=HEADERS)
assert_ok(r, "List my queries")

r = SESSION.get(f"{BASE}/queries/", headers=HEADERS)
assert_ok(r, "List all queries (boss)")

r = SESSION.post(f"{BASE}/queries/{query_id}/reply", headers=HEADERS, json={
    "reply": "Order placed, arriving Thursday", "status": "CLOSED"
})
assert_ok(r, "Reply to query")


# ============================================================================
# 10. INSTRUCTIONS
# ============================================================================
print("\n=== 10. INSTRUCTIONS ===")

r = SESSION.post(f"{BASE}/instructions", headers=HEADERS, json={
    "message": "Priority: Complete all staircase handrail cutting by EOD"
})
if assert_ok(r, "Create instruction"):
    instr_id = r.json()["id"]

r = SESSION.get(f"{BASE}/instructions", headers=HEADERS)
if assert_ok(r, "List instructions"):
    log("At least 1 instruction", len(r.json()) >= 1)

r = SESSION.put(f"{BASE}/instructions/{instr_id}", headers=HEADERS, json={
    "message": "UPDATED: Complete handrail cutting by tomorrow noon"
})
assert_ok(r, "Update instruction")

r = SESSION.get(f"{BASE}/instructions/{instr_id}", headers=HEADERS)
assert_ok(r, "Get single instruction")


# ============================================================================
# 11. NOTIFICATIONS
# ============================================================================
print("\n=== 11. NOTIFICATIONS ===")

r = SESSION.get(f"{BASE}/notifications/", headers=HEADERS)
assert_ok(r, "List notifications")

r = SESSION.get(f"{BASE}/notifications/settings", headers=HEADERS)
assert_ok(r, "Get notification settings")


# ============================================================================
# 12. USER SETTINGS
# ============================================================================
print("\n=== 12. USER SETTINGS ===")

r = SESSION.get(f"{BASE}/users/me", headers=HEADERS)
if assert_ok(r, "Get my profile"):
    log("Username is boss", r.json()["username"] == "boss")

r = SESSION.put(f"{BASE}/users/me", headers=HEADERS, json={
    "username": "boss", "email": "boss@kumarbros.com", "company": "Kumar Brothers Steel Pvt Ltd"
})
assert_ok(r, "Update profile")

# Change password (then change back)
r = SESSION.post(f"{BASE}/users/me/change-password", headers=HEADERS, json={
    "old_password": "Boss1234!",
    "new_password": "NewBoss5678!"
})
if assert_ok(r, "Change password"):
    # Change back
    r2 = SESSION.post(f"{BASE}/auth/login", json={"username": "boss", "password": "NewBoss5678!"})
    if r2.status_code == 200:
        new_token = r2.json()["access_token"]
        new_headers = {"Authorization": f"Bearer {new_token}"}
        r3 = SESSION.post(f"{BASE}/users/me/change-password", headers=new_headers, json={
            "old_password": "NewBoss5678!",
            "new_password": "Boss1234!"
        })
        log("Password changed back", r3.status_code == 200)
        HEADERS = new_headers


# ============================================================================
# 13. FRONTEND PAGES LOAD CHECK
# ============================================================================
print("\n=== 13. FRONTEND PAGES ===")

pages = [
    "login.html", "index.html", "register.html",
    "customers.html", "customer_add.html", "customer_edit.html",
    "raw_material.html", "materials.html", "scrap.html", "reusable.html",
    "grn.html", "dispatch.html", "tracking_v2.html", "drawings.html",
    "instructions.html", "queries.html", "settings.html",
    "account-settings.html", "notification-settings.html", "stock.html"
]

for page in pages:
    r = SESSION.get(f"{BASE}/{page}")
    ok = r.status_code == 200 and "<!doctype html>" in r.text.lower() or "<!DOCTYPE html>" in r.text
    log(f"Page loads: {page}", ok)

# Check Swagger docs
r = SESSION.get(f"{BASE}/docs")
log("Swagger UI loads", r.status_code == 200)

r = SESSION.get(f"{BASE}/redoc")
log("ReDoc loads", r.status_code == 200)


# ============================================================================
# 14. EDGE CASES & INPUT VALIDATION
# ============================================================================
print("\n=== 14. EDGE CASES ===")

# Empty body
r = SESSION.post(f"{BASE}/api/v3/drawings/", headers=HEADERS, json={})
log("Create drawing with empty body → 422", r.status_code == 422)

# XSS in input
r = SESSION.post(f"{BASE}/api/v3/drawings/", headers=HEADERS, json={
    "drawing_number": "<script>alert(1)</script>",
    "title": "XSS Test",
    "customer_id": cust_id
})
if r.status_code in (200, 201):
    xss_data = r.json()
    log("XSS stored but not executed (API returns raw)", "<script>" in xss_data.get("drawing_number", ""))

# Very long input
r = SESSION.post(f"{BASE}/api/v3/drawings/", headers=HEADERS, json={
    "drawing_number": "A" * 500,
    "title": "B" * 1000,
    "customer_id": cust_id
})
log(f"Very long input: HTTP {r.status_code}", r.status_code in (200, 201, 400, 422, 500))

# Negative weight
r = SESSION.post(f"{BASE}/api/v3/drawings/assemblies/{asm_id}/components", headers=HEADERS, json={
    "piece_mark": "NEG", "profile_section": "test", "quantity_per_assembly": 1,
    "weight_each_kg": -10
}) if 'asm_id' in dir() else None
if r:
    log("Negative weight rejected", r.status_code in (400, 422, 500))

# Zero quantity
r = SESSION.post(f"{BASE}/api/v3/drawings/assemblies/{asm_id}/components", headers=HEADERS, json={
    "piece_mark": "ZERO", "profile_section": "test", "quantity_per_assembly": 0,
    "weight_each_kg": 10
}) if 'asm_id' in dir() else None
if r:
    log(f"Zero quantity: HTTP {r.status_code}", True)

# Auth without token
r = SESSION.get(f"{BASE}/api/v3/drawings/")
log("No auth → 401", r.status_code == 401)

# Invalid token
r = SESSION.get(f"{BASE}/api/v3/drawings/", headers={"Authorization": "Bearer invalidtoken123"})
log("Bad token → 401", r.status_code == 401)


# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 60)
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
total = len(results)
print(f"RESULTS: {passed}/{total} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    print("\nFailed tests:")
    for r in results:
        if r["status"] == "FAIL":
            print(f"  FAIL {r['test']}: {r['detail']}")

print(f"\nExit code: {1 if failed > 0 else 0}")
exit(1 if failed > 0 else 0)
