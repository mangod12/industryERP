"""
Test EVERY page and EVERY API call as a real user would.
Simulates: login → navigate to each page → trigger every data load → test every form.
"""
import requests
import json
import sys

BASE = "http://127.0.0.1:8001"
S = requests.Session()
results = []
TOKEN = None

def t(name, ok, detail=""):
    results.append((name, ok, detail))
    mark = "OK" if ok else "FAIL"
    line = f"  {mark:4s} {name}"
    if not ok and detail:
        line += f" -- {detail[:120]}"
    print(line)
    return ok

def get(path, expect=200):
    r = S.get(f"{BASE}{path}", headers={"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})
    return t(f"GET {path}", r.status_code == expect, f"got {r.status_code}: {r.text[:100]}" if r.status_code != expect else ""), r

def post(path, data=None, expect=(200,201)):
    r = S.post(f"{BASE}{path}", json=data, headers={"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})
    ok = r.status_code in (expect if isinstance(expect, tuple) else (expect,))
    return t(f"POST {path}", ok, f"got {r.status_code}: {r.text[:100]}" if not ok else ""), r

def put(path, data=None, expect=200):
    r = S.put(f"{BASE}{path}", json=data, headers={"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})
    return t(f"PUT {path}", r.status_code == expect, f"got {r.status_code}: {r.text[:100]}" if r.status_code != expect else ""), r

# =====================================================================
print("\n=== LOGIN PAGE ===")
_, r = post("/auth/login", {"username": "boss", "password": "Boss1234!"})
TOKEN = r.json().get("access_token", "")
t("Got token", bool(TOKEN))

# =====================================================================
print("\n=== DASHBOARD (index.html) ===")
get("/index.html")
get("/dashboard/summary")
get("/inventory/dashboard-data")
get("/tracking/dashboard/summary")
get("/tracking/all-items")
get("/scrap/analytics?days=30")
get("/scrap/summary")
get("/notifications/")

# =====================================================================
print("\n=== CUSTOMERS PAGE (customers.html) ===")
get("/customers.html")
_, r = get("/customers")
customers = r.json() if r.status_code == 200 else []
t("Customers list is array", isinstance(customers, list))
_, r = get("/tracking/customers")
t("Tracking customers loads", r.status_code == 200)

# Create customer
_, r = post("/customers", {"name": "FlowTest Corp", "project_details": "Flow test project"})
if r.status_code in (200, 201):
    cid = r.json()["id"]
    t("Customer created", True)
else:
    cid = customers[0]["id"] if customers else None
    t("Using existing customer", bool(cid))

# Get single
if cid:
    get(f"/customers/{cid}")

# =====================================================================
print("\n=== CUSTOMER ADD (customer_add.html) ===")
get("/customer_add.html")

# =====================================================================
print("\n=== CUSTOMER EDIT (customer_edit.html) ===")
get("/customer_edit.html")
if cid:
    _, r = put(f"/customers/{cid}", {"name": "FlowTest Corp Updated", "project_details": "Updated"})

# =====================================================================
print("\n=== CUSTOMER DETAILS (customer_details.html) ===")
get("/customer_details.html")
if cid:
    get(f"/tracking/customers/{cid}")

# =====================================================================
print("\n=== INVENTORY PAGE (raw_material.html) ===")
get("/raw_material.html")
_, r = get("/inventory")
inv_items = r.json() if r.status_code == 200 else []
t("Inventory is array", isinstance(inv_items, list))
get("/inventory/stats/summary")
get("/mappings")

# Create inventory if needed
inv_id = None
for item in inv_items:
    if "UB203" in (item.get("name") or ""):
        inv_id = item["id"]
        break
if not inv_id:
    _, r = post("/inventory", {"name": "UB203X133X25-FLOW", "unit": "kg", "total": 5000, "used": 0, "code": "UB203F", "section": "UB203X133X25", "category": "Beam"})
    if r.status_code in (200, 201):
        inv_id = r.json()["id"]

if inv_id:
    _, r = put(f"/inventory/{inv_id}", {"name": inv_items[0]["name"] if inv_items else "UB203X133X25", "unit": "kg", "total": 5500, "used": 100, "code": "UB203", "section": "UB203X133X25", "category": "Beam"})

# =====================================================================
print("\n=== MATERIALS PAGE (materials.html) ===")
get("/materials.html")
get("/api/v2/inventory/materials")

# =====================================================================
print("\n=== SCRAP PAGE (scrap.html) ===")
get("/scrap.html")
get("/scrap/summary")
get("/scrap/analytics?days=30")
get("/scrap/records")
get("/customers")  # dropdown

# Create scrap
_, r = post("/scrap/records", {
    "material_name": "Flow Test Scrap",
    "weight_kg": 12.5,
    "quantity": 1,
    "reason_code": "cutting_waste",
    "notes": "Flow test"
})
scrap_id = r.json().get("id") if r.status_code in (200, 201) else None

# Filter scrap
get("/scrap/records?status=pending")
get("/scrap/records?reason_code=cutting_waste")
get("/scrap/records?material_name=Flow")

# =====================================================================
print("\n=== REUSABLE PAGE (reusable.html) ===")
get("/reusable.html")
get("/scrap/reusable")
get("/scrap/reusable?quality_grade=A")
get("/scrap/summary")
get("/scrap/analytics?days=30")

# =====================================================================
print("\n=== GRN PAGE (grn.html) ===")
get("/grn.html")
get("/api/v2/grn/")
get("/api/v2/grn/vendors")
get("/api/v2/inventory/materials")

# Create vendor (uses query params, not JSON body)
r = S.post(f"{BASE}/api/v2/grn/vendors?code=V-FLOW-001&name=Flow+Test+Vendor&city=Bangalore&contact_person=Test&phone=9876543210",
           headers={"Authorization": f"Bearer {TOKEN}"})
t("POST /api/v2/grn/vendors", r.status_code in (200, 201, 400), f"got {r.status_code}: {r.text[:80]}" if r.status_code not in (200, 201, 400) else "")
vendor_id = r.json().get("id") if r.status_code in (200, 201) else None

# Get existing vendor if create failed (duplicate)
if not vendor_id:
    vr = S.get(f"{BASE}/api/v2/grn/vendors", headers={"Authorization": f"Bearer {TOKEN}"})
    vendors = vr.json() if vr.status_code == 200 else []
    vendor_id = vendors[0]["id"] if vendors else None

# Create GRN
if vendor_id:
    _, r = post("/api/v2/grn/", {
        "vendor_id": vendor_id,
        "vehicle_number": "KA01AB1234",
        "driver_name": "Flow Driver"
    })

# =====================================================================
print("\n=== DISPATCH PAGE (dispatch.html) ===")
get("/dispatch.html")
get("/api/v2/dispatch/")
get("/customers")  # dropdown
get("/api/v2/inventory/materials")

# =====================================================================
print("\n=== TRACKING PAGE (tracking_v2.html) ===")
get("/tracking_v2.html")
get("/tracking/customers")
get("/api/tracking")
get("/api/tracking/all-items?page=1&page_size=10")
get("/api/tracking/completed")
get("/tracking/dashboard/summary")

# =====================================================================
print("\n=== DRAWINGS PAGE (drawings.html) ===")
get("/drawings.html")
get("/api/v3/drawings/")
get("/api/v3/drawings")
get("/customers")  # dropdown
get("/api/v3/drawings/kanban")

# Create drawing
import time
run_id = str(int(time.time()))[-6:]
_, r = post("/api/v3/drawings/", {
    "drawing_number": f"FLOW-{run_id}",
    "title": "Flow Test Drawing",
    "customer_id": cid,
})
if r.status_code in (200, 201):
    dwg_id = r.json()["id"]
    t("Drawing created", True)

    # Add assembly
    _, r = post(f"/api/v3/drawings/{dwg_id}/assemblies", {
        "mark_number": "FA1", "description": "Flow assembly", "quantity_required": 2
    })
    if r.status_code in (200, 201):
        asm_id = r.json()["id"]

        # Add components
        post(f"/api/v3/drawings/assemblies/{asm_id}/components", {
            "piece_mark": "FP1", "profile_section": "UB203X133X25",
            "grade": "S275", "length_mm": 3000, "quantity_per_assembly": 1,
            "weight_each_kg": 75.0, "inventory_id": inv_id
        })
        post(f"/api/v3/drawings/assemblies/{asm_id}/components", {
            "piece_mark": "FP2", "profile_section": "50x50x5 SHS",
            "quantity_per_assembly": 2, "weight_each_kg": 8.0
        })

    # Release
    _, r = post(f"/api/v3/drawings/{dwg_id}/release")
    t("Drawing released", r.status_code == 200)

    # Progress
    get(f"/api/v3/drawings/{dwg_id}/progress")

    # Material usage
    _, r = get(f"/api/v3/drawings/{dwg_id}/material-usage")
    if r.status_code == 200:
        mu = r.json()
        t("Material usage has assemblies", len(mu.get("assemblies", [])) > 0)
        t("BOM weight > 0", mu.get("total_bom_weight_kg", 0) > 0)

    # Detail
    _, r = get(f"/api/v3/drawings/{dwg_id}")
    if r.status_code == 200:
        data = r.json()
        instances = data.get("instance_count", 0)
        t(f"Instances created ({instances})", instances == 6)

        # Find instance IDs from kanban
        _, kr = get(f"/api/v3/drawings/kanban?drawing_id={dwg_id}")
        if kr.status_code == 200:
            kanban = kr.json()
            cutting = next((c for c in kanban.get("columns", []) if c["stage_name"] == "cutting"), None)
            if cutting and cutting.get("instances"):
                iid = cutting["instances"][0]["id"]
                # Start
                post(f"/api/v3/drawings/instances/{iid}/start")
                # Advance
                _, ar = post(f"/api/v3/drawings/instances/{iid}/advance", {
                    "component_instance_id": iid, "remarks": "Flow test advance"
                })
                t("Instance advanced", ar.status_code == 200)

                # Hold another
                if len(cutting["instances"]) > 1:
                    iid2 = cutting["instances"][1]["id"]
                    post(f"/api/v3/drawings/instances/{iid2}/start")
                    post(f"/api/v3/drawings/instances/{iid2}/hold", {"reason": "Flow test hold"})

    # Kanban after changes
    get(f"/api/v3/drawings/kanban?drawing_id={dwg_id}")

# Filter drawings
get(f"/api/v3/drawings/?customer_id={cid}")
get("/api/v3/drawings/?status=released")

# =====================================================================
print("\n=== INSTRUCTIONS PAGE (instructions.html) ===")
get("/instructions.html")
_, r = get("/instructions")
instructions = r.json() if r.status_code == 200 else []
t("Instructions is array", isinstance(instructions, list))

# Create
_, r = post("/instructions", {"message": "Flow test instruction"})
if r.status_code in (200, 201):
    iid = r.json()["id"]
    get(f"/instructions/{iid}")
    put(f"/instructions/{iid}", {"message": "Updated flow instruction"})

# =====================================================================
print("\n=== QUERIES PAGE (queries.html) ===")
get("/queries.html")
get("/users/me")
get("/queries/")
get("/queries/me")

# Create query
_, r = post("/queries/", {"title": "Flow test query", "message": "Testing query flow"})
if r.status_code in (200, 201):
    qid = r.json()["id"]
    # Reply
    post(f"/queries/{qid}/reply", {"reply": "Flow test reply", "status": "CLOSED"})

# =====================================================================
print("\n=== SETTINGS PAGE (settings.html) ===")
get("/settings.html")

# =====================================================================
print("\n=== ACCOUNT SETTINGS (account-settings.html) ===")
get("/account-settings.html")
get("/users/me")

# =====================================================================
print("\n=== NOTIFICATION SETTINGS (notification-settings.html) ===")
get("/notification-settings.html")
get("/notifications/settings")

# =====================================================================
print("\n=== STOCK PAGE (stock.html) ===")
get("/stock.html")
get("/api/v2/inventory/materials")

# The stock page calls /api/v2/inventory/stock which doesn't exist as a separate endpoint
# It should be /api/v2/inventory/lots
r = S.get(f"{BASE}/api/v2/inventory/stock?limit=25", headers={"Authorization": f"Bearer {TOKEN}"})
t("GET /api/v2/inventory/stock", r.status_code == 200, f"got {r.status_code}" if r.status_code != 200 else "")

_, r = get("/api/v2/inventory/lots")

# =====================================================================
print("\n=== REGISTER PAGE (register.html) ===")
get("/register.html")

# =====================================================================
print("\n=== EXCEL ENDPOINTS ===")
get("/excel/template")

# =====================================================================
print("\n=== NOTIFICATIONS ===")
get("/notifications/")
get("/notifications")
post("/notifications/mark-read", {"ids": []}, expect=(200, 400, 422))

# =====================================================================
print("\n=== ALL STATIC PAGES LOAD ===")
pages = [
    "login.html", "index.html", "register.html", "customers.html",
    "customer_add.html", "customer_edit.html", "customer_details.html",
    "raw_material.html", "materials.html", "scrap.html", "reusable.html",
    "grn.html", "dispatch.html", "tracking_v2.html", "drawings.html",
    "instructions.html", "queries.html", "settings.html",
    "account-settings.html", "notification-settings.html", "stock.html",
]
for p in pages:
    r = S.get(f"{BASE}/{p}")
    ok = r.status_code == 200 and ("<!doctype" in r.text.lower() or "<!DOCTYPE" in r.text)
    t(f"Page: {p}", ok, f"HTTP {r.status_code}" if not ok else "")

# Assets
for f in ["css/main.css", "js/config.js", "js/main.js"]:
    r = S.get(f"{BASE}/{f}")
    t(f"Asset: {f}", r.status_code == 200)

# Swagger
get("/docs")
get("/redoc")

# =====================================================================
print("\n" + "=" * 70)
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
print(f"TOTAL: {passed}/{len(results)} passed, {failed} failed")
print("=" * 70)
if failed:
    print("\nFAILED:")
    for name, ok, detail in results:
        if not ok:
            print(f"  {name}: {detail}")
sys.exit(1 if failed else 0)
