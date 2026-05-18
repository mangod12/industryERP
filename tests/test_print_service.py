"""
Tests for the Print Format Engine
===================================
Covers:
- HTML rendering for each template
- PDF generation returns valid bytes
- GRN document data gathering
- Dispatch document data gathering
- Missing document returns 404
- Company info loads from system_config (or defaults)
"""

import os
import sys
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

# Ensure the backend_core package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend_core"))

from backend_core.app.services.print_service import PrintService, _fmt_currency, _fmt_weight

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_vendor(**overrides):
    v = MagicMock()
    v.id = overrides.get("id", 1)
    v.code = overrides.get("code", "V001")
    v.name = overrides.get("name", "Test Vendor")
    v.gstin = overrides.get("gstin", "29AABCT1332L1ZP")
    v.address = overrides.get("address", "Industrial Area")
    v.city = overrides.get("city", "Bokaro")
    v.phone = overrides.get("phone", "9876543210")
    return v


def _make_material(**overrides):
    m = MagicMock()
    m.id = overrides.get("id", 1)
    m.code = overrides.get("code", "STL-COIL-HR-2.5")
    m.name = overrides.get("name", "HR Coil 2.5mm")
    return m


def _make_grn_line(material, **overrides):
    line = MagicMock()
    line.id = overrides.get("id", 1)
    line.material_id = material.id
    line.heat_number = overrides.get("heat_number", "HN-001")
    line.batch_number = overrides.get("batch_number", "B-001")
    line.received_qty = Decimal(overrides.get("received_qty", "10"))
    line.weight_kg = Decimal(overrides.get("weight_kg", "5000"))
    line.unit = MagicMock()
    line.unit.value = "kg"
    line.rate = Decimal(overrides.get("rate", "45.50"))
    line.amount = None
    line.qa_status = MagicMock()
    line.qa_status.value = overrides.get("qa_status", "approved")
    return line


def _make_grn(vendor, lines, **overrides):
    grn = MagicMock()
    grn.id = overrides.get("id", 1)
    grn.grn_number = overrides.get("grn_number", "GRN/2526/000001")
    grn.vendor_id = vendor.id
    grn.vehicle_number = overrides.get("vehicle_number", "JH01AB1234")
    grn.driver_name = overrides.get("driver_name", "Ram Kumar")
    grn.weighbridge_slip_number = overrides.get("weighbridge_slip", "WB-101")
    grn.gross_weight_kg = Decimal(overrides.get("gross_weight_kg", "15000"))
    grn.tare_weight_kg = Decimal(overrides.get("tare_weight_kg", "5000"))
    grn.net_weight_kg = Decimal(overrides.get("net_weight_kg", "10000"))
    grn.status = MagicMock()
    grn.status.value = overrides.get("status", "approved")
    grn.gate_entry_time = datetime(2025, 6, 1, 8, 0)
    grn.weighment_time = datetime(2025, 6, 1, 8, 30)
    grn.received_time = datetime(2025, 6, 1, 9, 0)
    grn.vendor_invoice_number = overrides.get("vendor_invoice_number", "INV-100")
    grn.vendor_invoice_date = datetime(2025, 5, 30)
    grn.created_at = datetime(2025, 6, 1, 8, 0)
    grn.remarks = overrides.get("remarks", "Test GRN")
    grn.line_items = lines
    return grn


def _make_stock_lot(material, **overrides):
    lot = MagicMock()
    lot.id = overrides.get("id", 1)
    lot.lot_number = overrides.get("lot_number", "LOT/2526/000001")
    lot.material_id = material.id
    lot.heat_number = overrides.get("heat_number", "HN-001")
    lot.current_weight_kg = Decimal(overrides.get("current_weight_kg", "5000"))
    return lot


def _make_dispatch_line(lot, **overrides):
    line = MagicMock()
    line.id = overrides.get("id", 1)
    line.stock_lot_id = lot.id
    line.dispatched_weight_kg = Decimal(overrides.get("weight_kg", "3000"))
    line.dispatched_qty = Decimal(overrides.get("qty", "1"))
    line.rate = Decimal(overrides.get("rate", "50.00"))
    line.amount = None
    return line


def _make_customer(**overrides):
    c = MagicMock()
    c.id = overrides.get("id", 1)
    c.name = overrides.get("name", "Test Customer")
    c.phone = overrides.get("phone", "9876543210")
    c.email = overrides.get("email", "customer@example.com")
    return c


def _make_dispatch(customer, lines, **overrides):
    d = MagicMock()
    d.id = overrides.get("id", 1)
    d.dispatch_number = overrides.get("dispatch_number", "DSP/2526/000001")
    d.customer_id = customer.id
    d.sales_order_ref = overrides.get("sales_order_ref", "SO-200")
    d.vehicle_number = overrides.get("vehicle_number", "JH02CD5678")
    d.transporter = overrides.get("transporter", "Fast Transport")
    d.driver_name = overrides.get("driver_name", "Shyam")
    d.driver_contact = overrides.get("driver_contact", "9876500000")
    d.gross_weight_kg = Decimal(overrides.get("gross_weight_kg", "12000"))
    d.tare_weight_kg = Decimal(overrides.get("tare_weight_kg", "4000"))
    d.net_weight_kg = Decimal(overrides.get("net_weight_kg", "8000"))
    d.status = MagicMock()
    d.status.value = overrides.get("status", "approved")
    d.dispatched_at = datetime(2025, 6, 2, 14, 0)
    d.created_at = datetime(2025, 6, 2, 10, 0)
    d.remarks = overrides.get("remarks", "")
    d.line_items = lines
    return d


def _mock_db_for_grn():
    """Return a mock db Session pre-loaded with GRN data."""
    vendor = _make_vendor()
    material = _make_material()
    line = _make_grn_line(material)
    grn = _make_grn(vendor, [line])

    db = MagicMock()

    def query_side_effect(model):
        q = MagicMock()
        if model.__name__ == "GoodsReceiptNote":
            q.filter.return_value.first.return_value = grn
        elif model.__name__ == "Vendor":
            q.filter.return_value.first.return_value = vendor
        elif model.__name__ == "MaterialMaster":
            q.filter.return_value.first.return_value = material
        elif model.__name__ == "SystemConfig":
            q.filter.return_value.all.return_value = []
        else:
            q.filter.return_value.first.return_value = None
            q.filter.return_value.all.return_value = []
        return q

    db.query.side_effect = query_side_effect
    return db, grn, vendor, material


def _mock_db_for_dispatch():
    """Return a mock db Session pre-loaded with Dispatch data."""
    customer = _make_customer()
    material = _make_material()
    lot = _make_stock_lot(material)
    line = _make_dispatch_line(lot)
    dispatch = _make_dispatch(customer, [line])

    db = MagicMock()

    def query_side_effect(model):
        q = MagicMock()
        name = model.__name__
        if name == "DispatchNote":
            q.filter.return_value.first.return_value = dispatch
        elif name == "Customer":
            q.filter.return_value.first.return_value = customer
        elif name == "StockLot":
            q.filter.return_value.first.return_value = lot
        elif name == "MaterialMaster":
            q.filter.return_value.first.return_value = material
        elif name == "SystemConfig":
            q.filter.return_value.all.return_value = []
        else:
            q.filter.return_value.first.return_value = None
            q.filter.return_value.all.return_value = []
        return q

    db.query.side_effect = query_side_effect
    return db, dispatch, customer, material


# ---------------------------------------------------------------------------
# Tests — Helper Functions
# ---------------------------------------------------------------------------


class TestFormatHelpers:
    def test_fmt_weight_none(self):
        assert _fmt_weight(None) == "\u2014"

    def test_fmt_weight_value(self):
        result = _fmt_weight(5000.123)
        assert "5,000.123" in result

    def test_fmt_currency_none(self):
        assert _fmt_currency(None) == "\u2014"

    def test_fmt_currency_value(self):
        result = _fmt_currency(12345.6)
        assert "12,345.60" in result


# ---------------------------------------------------------------------------
# Tests — Company Info
# ---------------------------------------------------------------------------


class TestCompanyInfo:
    def test_defaults_when_no_config(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        info = PrintService.get_company_info(db)
        assert info["name"] == "KumarBrothers Steel"
        assert "address" in info
        assert "gstin" in info

    def test_loads_from_system_config(self):
        row = MagicMock()
        row.key = "company_name"
        row.value = "Custom Steel Corp"

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [row]
        info = PrintService.get_company_info(db)
        assert info["name"] == "Custom Steel Corp"


# ---------------------------------------------------------------------------
# Tests — GRN Document
# ---------------------------------------------------------------------------


class TestGRNDocument:
    def test_generate_grn_document(self):
        db, grn, vendor, material = _mock_db_for_grn()
        result = PrintService.generate_grn_document(db, 1)

        assert result["grn_number"] == "GRN/2526/000001"
        assert result["vendor"]["name"] == "Test Vendor"
        assert len(result["line_items"]) == 1
        assert result["total_weight_kg"] == 5000.0
        assert result["document_title"] == "Goods Receipt Note"

    def test_grn_not_found_raises(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(ValueError, match="not found"):
            PrintService.generate_grn_document(db, 999)


# ---------------------------------------------------------------------------
# Tests — Dispatch Document
# ---------------------------------------------------------------------------


class TestDispatchDocument:
    def test_generate_dispatch_document(self):
        db, dispatch, customer, material = _mock_db_for_dispatch()
        result = PrintService.generate_dispatch_document(db, 1)

        assert result["dispatch_number"] == "DSP/2526/000001"
        assert result["customer"]["name"] == "Test Customer"
        assert len(result["line_items"]) == 1
        assert result["total_weight_kg"] == 3000.0
        assert result["document_title"] == "Dispatch Note"

    def test_dispatch_not_found_raises(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(ValueError, match="not found"):
            PrintService.generate_dispatch_document(db, 999)


# ---------------------------------------------------------------------------
# Tests — Delivery Challan
# ---------------------------------------------------------------------------


class TestDeliveryChallan:
    def test_generate_delivery_challan(self):
        db, dispatch, customer, material = _mock_db_for_dispatch()
        result = PrintService.generate_delivery_challan(db, 1)

        assert result["document_title"] == "Delivery Challan"
        # Challan should strip pricing
        for item in result["line_items"]:
            assert "rate" not in item
            assert "amount" not in item
        assert "total_amount" not in result


# ---------------------------------------------------------------------------
# Tests — HTML Rendering
# ---------------------------------------------------------------------------


class TestHTMLRendering:
    def test_grn_html_renders(self):
        db, grn, vendor, material = _mock_db_for_grn()
        context = PrintService.generate_grn_document(db, 1)
        html = PrintService.render_html("grn.html", context)

        assert "GRN/2526/000001" in html
        assert "Test Vendor" in html
        assert "Goods Receipt Note" in html
        assert "<table" in html

    def test_dispatch_html_renders(self):
        db, dispatch, customer, material = _mock_db_for_dispatch()
        context = PrintService.generate_dispatch_document(db, 1)
        html = PrintService.render_html("dispatch_note.html", context)

        assert "DSP/2526/000001" in html
        assert "Test Customer" in html
        assert "Dispatch Note" in html

    def test_challan_html_renders(self):
        db, dispatch, customer, material = _mock_db_for_dispatch()
        context = PrintService.generate_delivery_challan(db, 1)
        html = PrintService.render_html("delivery_challan.html", context)

        assert "Delivery Challan" in html
        assert "DSP/2526/000001" in html
        # Should NOT contain rate/amount columns (pricing stripped)
        assert "Rate" not in html


# ---------------------------------------------------------------------------
# Tests — PDF Generation
# ---------------------------------------------------------------------------


class TestPDFGeneration:
    def test_grn_pdf_has_valid_header(self):
        db, grn, vendor, material = _mock_db_for_grn()
        context = PrintService.generate_grn_document(db, 1)

        try:
            pdf_buffer = PrintService.render_pdf("grn.html", context)
        except ImportError:
            pytest.skip("xhtml2pdf not installed")

        pdf_bytes = pdf_buffer.read()
        assert pdf_bytes[:5] == b"%PDF-"
        assert len(pdf_bytes) > 100

    def test_dispatch_pdf_has_valid_header(self):
        db, dispatch, customer, material = _mock_db_for_dispatch()
        context = PrintService.generate_dispatch_document(db, 1)

        try:
            pdf_buffer = PrintService.render_pdf("dispatch_note.html", context)
        except ImportError:
            pytest.skip("xhtml2pdf not installed")

        pdf_bytes = pdf_buffer.read()
        assert pdf_bytes[:5] == b"%PDF-"


# ---------------------------------------------------------------------------
# Tests — Router (FastAPI TestClient)
# ---------------------------------------------------------------------------


class TestPrintRouter:
    """Integration tests using FastAPI TestClient."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        """Create a test client with mocked dependencies."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from backend_core.app.routers.print_formats import router
        from backend_core.app.security import get_current_user

        app = FastAPI()
        app.include_router(router)

        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.role = "admin"

        app.dependency_overrides[get_current_user] = lambda: mock_user

        self.app = app
        self.mock_user = mock_user
        self.TestClient = TestClient
        yield

    def test_invalid_document_type_returns_400(self):
        db = MagicMock()
        from backend_core.app.security import get_db

        self.app.dependency_overrides[get_db] = lambda: db

        client = self.TestClient(self.app)
        resp = client.get("/api/v2/print/invalid/1")
        assert resp.status_code == 400
        assert "Unknown document type" in resp.json()["detail"]

    def test_missing_grn_returns_404(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        from backend_core.app.security import get_db

        self.app.dependency_overrides[get_db] = lambda: db

        client = self.TestClient(self.app)
        resp = client.get("/api/v2/print/grn/999")
        assert resp.status_code == 404

    def test_grn_html_returns_200(self):
        db, grn, vendor, material = _mock_db_for_grn()
        from backend_core.app.security import get_db

        self.app.dependency_overrides[get_db] = lambda: db

        client = self.TestClient(self.app)
        resp = client.get("/api/v2/print/grn/1?format=html")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "GRN/2526/000001" in resp.text

    def test_dispatch_html_returns_200(self):
        db, dispatch, customer, material = _mock_db_for_dispatch()
        from backend_core.app.security import get_db

        self.app.dependency_overrides[get_db] = lambda: db

        client = self.TestClient(self.app)
        resp = client.get("/api/v2/print/dispatch/1?format=html")
        assert resp.status_code == 200
        assert "DSP/2526/000001" in resp.text

    def test_challan_html_returns_200(self):
        db, dispatch, customer, material = _mock_db_for_dispatch()
        from backend_core.app.security import get_db

        self.app.dependency_overrides[get_db] = lambda: db

        client = self.TestClient(self.app)
        resp = client.get("/api/v2/print/challan/1?format=html")
        assert resp.status_code == 200
        assert "Delivery Challan" in resp.text
