"""
Print Formats API Router
=========================
Generate printable HTML and PDF documents for GRN, Dispatch, and Delivery Challan.

Endpoints:
    GET /api/v2/print/{document_type}/{document_id}?format=html|pdf
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session

from ..security import get_current_user, get_db
from ..services.print_service import PrintService

router = APIRouter(prefix="/api/v2/print", tags=["Print Formats"])

# Map document_type parameter to (generator function, template file)
_DOCUMENT_MAP = {
    "grn": ("generate_grn_document", "grn.html"),
    "dispatch": ("generate_dispatch_document", "dispatch_note.html"),
    "challan": ("generate_delivery_challan", "delivery_challan.html"),
}


@router.get("/{document_type}/{document_id}")
def get_print_document(
    document_type: str,
    document_id: int,
    format: str = Query("html", pattern="^(html|pdf)$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Generate a printable document.

    **document_type**: ``grn``, ``dispatch``, or ``challan``

    **format**: ``html`` (default) or ``pdf``
    """
    if document_type not in _DOCUMENT_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown document type '{document_type}'. Valid types: {', '.join(_DOCUMENT_MAP.keys())}",
        )

    generator_name, template_name = _DOCUMENT_MAP[document_type]
    generator = getattr(PrintService, generator_name)

    try:
        context = generator(db, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if format == "pdf":
        pdf_buffer = PrintService.render_pdf(template_name, context)
        filename = f"{document_type}_{document_id}.pdf"
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename={filename}"},
        )

    html = PrintService.render_html(template_name, context)
    return HTMLResponse(content=html)
