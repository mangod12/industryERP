"""
Print Service — Document Generation for Steel Industry
========================================================
Generates printable HTML and PDF documents for:
- GRN (Goods Receipt Notes)
- Dispatch Notes
- Delivery Challans

Uses Jinja2 for HTML templating and xhtml2pdf for PDF conversion.
"""

from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from ..models import Customer
from ..models_v2 import (
    DispatchNote,
    GoodsReceiptNote,
    MaterialMaster,
    StockLot,
    SystemConfig,
    Vendor,
)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "print"


def _build_jinja_env() -> Environment:
    """Create a Jinja2 environment pointed at the print templates directory."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def _fmt_weight(value) -> str:
    """Format a weight value to 3 decimal places with comma grouping."""
    if value is None:
        return "—"
    return f"{float(value):,.3f}"


def _fmt_currency(value) -> str:
    """Format a currency value to 2 decimal places with comma grouping."""
    if value is None:
        return "—"
    return f"{float(value):,.2f}"


def _fmt_date(value) -> str:
    """Format a datetime to a human-readable date string."""
    if value is None:
        return "—"
    if isinstance(value, str):
        return value
    return value.strftime("%d-%b-%Y")


def _fmt_datetime(value) -> str:
    """Format a datetime to a human-readable date-time string."""
    if value is None:
        return "—"
    if isinstance(value, str):
        return value
    return value.strftime("%d-%b-%Y %H:%M")


class PrintService:
    """Generate printable documents from Jinja2 templates."""

    @staticmethod
    def render_html(template_name: str, context: dict) -> str:
        """Render a Jinja2 template to an HTML string."""
        env = _build_jinja_env()
        env.filters["fmt_weight"] = _fmt_weight
        env.filters["fmt_currency"] = _fmt_currency
        env.filters["fmt_date"] = _fmt_date
        env.filters["fmt_datetime"] = _fmt_datetime
        template = env.get_template(template_name)
        return template.render(**context)

    @staticmethod
    def render_pdf(template_name: str, context: dict) -> BytesIO:
        """Render a Jinja2 template to a PDF via xhtml2pdf."""
        from xhtml2pdf import pisa  # lazy import to keep startup fast

        html = PrintService.render_html(template_name, context)
        buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=buffer)
        if pisa_status.err:
            raise RuntimeError(f"PDF generation failed with {pisa_status.err} errors")
        buffer.seek(0)
        return buffer

    @staticmethod
    def get_company_info(db: Session) -> dict:
        """
        Load company info from the system_config table.

        Expected keys: company_name, company_address, company_gstin,
        company_phone, company_email, company_logo_url.
        Falls back to sensible defaults for KumarBrothers Steel.
        """
        defaults = {
            "company_name": "KumarBrothers Steel",
            "company_address": "",
            "company_gstin": "",
            "company_phone": "",
            "company_email": "",
            "company_logo_url": "",
        }

        rows = db.query(SystemConfig).filter(SystemConfig.key.in_(list(defaults.keys()))).all()

        info = dict(defaults)
        for row in rows:
            if row.value:
                info[row.key] = row.value

        return {
            "name": info["company_name"],
            "address": info["company_address"],
            "gstin": info["company_gstin"],
            "phone": info["company_phone"],
            "email": info["company_email"],
            "logo_url": info["company_logo_url"],
        }

    @staticmethod
    def generate_grn_document(db: Session, grn_id: int) -> dict:
        """
        Gather all data needed to print a GRN document.

        Returns a dict ready to be passed as Jinja2 context.
        Raises ValueError if the GRN does not exist.
        """
        grn = db.query(GoodsReceiptNote).filter(GoodsReceiptNote.id == grn_id).first()

        if not grn:
            raise ValueError(f"GRN with id {grn_id} not found")

        vendor = db.query(Vendor).filter(Vendor.id == grn.vendor_id).first()

        line_items = []
        total_weight = Decimal("0")
        total_amount = Decimal("0")

        for line in grn.line_items:
            material = db.query(MaterialMaster).filter(MaterialMaster.id == line.material_id).first()

            amount = (line.rate * line.weight_kg) if line.rate else None
            if amount:
                total_amount += amount

            total_weight += line.weight_kg

            line_items.append(
                {
                    "material_code": material.code if material else "—",
                    "material_name": material.name if material else "—",
                    "heat_number": line.heat_number or "—",
                    "batch_number": line.batch_number or "—",
                    "received_qty": float(line.received_qty),
                    "weight_kg": float(line.weight_kg),
                    "unit": line.unit.value if line.unit else "kg",
                    "rate": float(line.rate) if line.rate else None,
                    "amount": float(amount) if amount else None,
                    "qa_status": line.qa_status.value if line.qa_status else "pending",
                }
            )

        company = PrintService.get_company_info(db)

        return {
            "company": company,
            "document_title": "Goods Receipt Note",
            "grn_number": grn.grn_number,
            "grn_date": grn.created_at,
            "status": grn.status.value if grn.status else "draft",
            "vendor": {
                "name": vendor.name if vendor else "—",
                "code": vendor.code if vendor else "—",
                "gstin": vendor.gstin if vendor else "—",
                "address": vendor.address if vendor else "—",
                "city": vendor.city if vendor else "—",
                "phone": vendor.phone if vendor else "—",
            }
            if vendor
            else {},
            "vehicle_number": grn.vehicle_number or "—",
            "driver_name": grn.driver_name or "—",
            "weighbridge_slip": grn.weighbridge_slip_number or "—",
            "gross_weight_kg": float(grn.gross_weight_kg) if grn.gross_weight_kg else None,
            "tare_weight_kg": float(grn.tare_weight_kg) if grn.tare_weight_kg else None,
            "net_weight_kg": float(grn.net_weight_kg) if grn.net_weight_kg else None,
            "gate_entry_time": grn.gate_entry_time,
            "weighment_time": grn.weighment_time,
            "received_time": grn.received_time,
            "vendor_invoice_number": grn.vendor_invoice_number or "—",
            "vendor_invoice_date": grn.vendor_invoice_date,
            "line_items": line_items,
            "total_weight_kg": float(total_weight),
            "total_amount": float(total_amount),
            "remarks": grn.remarks or "",
            "print_date": datetime.now(),
        }

    @staticmethod
    def generate_dispatch_document(db: Session, dispatch_id: int) -> dict:
        """
        Gather all data needed to print a Dispatch Note.

        Returns a dict ready to be passed as Jinja2 context.
        Raises ValueError if the dispatch does not exist.
        """
        dispatch = db.query(DispatchNote).filter(DispatchNote.id == dispatch_id).first()

        if not dispatch:
            raise ValueError(f"Dispatch with id {dispatch_id} not found")

        customer = db.query(Customer).filter(Customer.id == dispatch.customer_id).first()

        line_items = []
        total_weight = Decimal("0")
        total_amount = Decimal("0")

        for line in dispatch.line_items:
            lot = db.query(StockLot).filter(StockLot.id == line.stock_lot_id).first()
            material = db.query(MaterialMaster).filter(MaterialMaster.id == lot.material_id).first() if lot else None

            amount = line.amount or ((line.rate * line.dispatched_weight_kg) if line.rate else None)
            if amount:
                total_amount += amount

            total_weight += line.dispatched_weight_kg

            line_items.append(
                {
                    "lot_number": lot.lot_number if lot else "—",
                    "material_code": material.code if material else "—",
                    "material_name": material.name if material else "—",
                    "heat_number": lot.heat_number if lot else "—",
                    "dispatched_weight_kg": float(line.dispatched_weight_kg),
                    "dispatched_qty": float(line.dispatched_qty) if line.dispatched_qty else 1,
                    "rate": float(line.rate) if line.rate else None,
                    "amount": float(amount) if amount else None,
                }
            )

        company = PrintService.get_company_info(db)

        return {
            "company": company,
            "document_title": "Dispatch Note",
            "dispatch_number": dispatch.dispatch_number,
            "dispatch_date": dispatch.created_at,
            "status": dispatch.status.value if dispatch.status else "draft",
            "customer": {
                "name": customer.name if customer else "—",
                "phone": customer.phone if customer else "—",
                "email": customer.email if customer else "—",
            }
            if customer
            else {},
            "sales_order_ref": dispatch.sales_order_ref or "—",
            "vehicle_number": dispatch.vehicle_number or "—",
            "transporter": dispatch.transporter or "—",
            "driver_name": dispatch.driver_name or "—",
            "driver_contact": dispatch.driver_contact or "—",
            "gross_weight_kg": float(dispatch.gross_weight_kg) if dispatch.gross_weight_kg else None,
            "tare_weight_kg": float(dispatch.tare_weight_kg) if dispatch.tare_weight_kg else None,
            "net_weight_kg": float(dispatch.net_weight_kg) if dispatch.net_weight_kg else None,
            "dispatched_at": dispatch.dispatched_at,
            "line_items": line_items,
            "total_weight_kg": float(total_weight),
            "total_amount": float(total_amount),
            "remarks": dispatch.remarks or "",
            "print_date": datetime.now(),
        }

    @staticmethod
    def generate_delivery_challan(db: Session, dispatch_id: int) -> dict:
        """
        Gather data for a Delivery Challan (simplified dispatch for transport).

        Same data as dispatch but the template omits rates/values.
        Raises ValueError if the dispatch does not exist.
        """
        data = PrintService.generate_dispatch_document(db, dispatch_id)
        data["document_title"] = "Delivery Challan"
        # Strip pricing from line items for the driver copy
        for item in data["line_items"]:
            item.pop("rate", None)
            item.pop("amount", None)
        data.pop("total_amount", None)
        return data
