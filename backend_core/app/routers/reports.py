"""
Report Builder API
==================
Provides a unified endpoint for running predefined reports with filters
and exporting them to Excel.

All endpoints require authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..services.report_service import REPORT_DESCRIPTIONS, REPORT_REGISTRY, ReportService

router = APIRouter(prefix="/api/v2/reports", tags=["Reports"])


@router.get("/")
def list_reports(user=Depends(get_current_user)):
    """List all available reports with their descriptions."""
    reports = []
    for name in REPORT_REGISTRY:
        reports.append(
            {
                "name": name,
                "description": REPORT_DESCRIPTIONS.get(name, ""),
            }
        )
    return {"success": True, "data": {"reports": reports}}


@router.get("/{report_name}")
def get_report(
    report_name: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Run a report with query params as filters.

    Example: /api/v2/reports/stock-balance?material_id=5&location_id=2
    """
    report_fn = REPORT_REGISTRY.get(report_name)
    if report_fn is None:
        raise HTTPException(status_code=404, detail=f"Report '{report_name}' not found")

    # Collect all query params as filters (exclude internal FastAPI params)
    filters = dict(request.query_params)

    result = report_fn(db, filters=filters)
    return {"success": True, "data": result}


@router.get("/{report_name}/export")
def export_report(
    report_name: str,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Export report as Excel (.xlsx) file."""
    report_fn = REPORT_REGISTRY.get(report_name)
    if report_fn is None:
        raise HTTPException(status_code=404, detail=f"Report '{report_name}' not found")

    filters = dict(request.query_params)
    result = report_fn(db, filters=filters)

    excel_buffer = ReportService.export_to_excel(result, report_name)

    filename = f"{report_name}_{__import__('datetime').date.today().isoformat()}.xlsx"

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
