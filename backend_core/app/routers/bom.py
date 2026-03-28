"""
BOM (Bill of Materials) REST API — /api/v2/bom/
================================================
Endpoints for assembly + parts CRUD, material requirements,
CSV/Excel import, and template downloads.
"""
import io
import logging
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from ..deps import get_db, require_role, get_current_user
from .. import models
from ..models_bom import Assembly, AssemblyPart, AssemblyMaterialRequirement
from ..schemas_bom import (
    AssemblyCreate,
    AssemblyUpdate,
    AssemblyOut,
    AssemblyListOut,
    AssemblyPartCreate,
    AssemblyPartUpdate,
    AssemblyPartOut,
    MaterialRequirementOut,
    CSVImportResult,
)
from ..services.bom_service import BOMService
from ..services.stage_service import StageService
from ..services import csv_template_service
from ..schemas_bom import PieceCompletionUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/bom", tags=["bom"])


# ---------------------------------------------------------------------------
# Assembly CRUD
# ---------------------------------------------------------------------------

@router.post("/assemblies", response_model=AssemblyOut)
def create_assembly(
    data: AssemblyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    """Create an assembly with optional inline parts."""
    try:
        parts_dicts = [p.dict() for p in data.parts] if data.parts else None
        assembly = BOMService.create_assembly(
            db=db,
            customer_id=data.customer_id,
            assembly_code=data.assembly_code,
            assembly_name=data.assembly_name,
            drawing_number=data.drawing_number,
            revision=data.revision,
            ordered_qty=data.ordered_qty,
            lot_number=data.lot_number,
            notes=data.notes,
            parts=parts_dicts,
        )
        return assembly
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assemblies", response_model=list[AssemblyListOut])
def list_assemblies(
    customer_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    lot_number: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List assemblies with optional filters."""
    return BOMService.list_assemblies(db, customer_id, search, lot_number, skip, limit)


@router.get("/assemblies/{assembly_id}", response_model=AssemblyOut)
def get_assembly(
    assembly_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get assembly detail with nested parts and stage tracking."""
    assembly = BOMService.get_assembly(db, assembly_id)
    if not assembly:
        raise HTTPException(status_code=404, detail="Assembly not found")
    return assembly


@router.put("/assemblies/{assembly_id}", response_model=AssemblyOut)
def update_assembly(
    assembly_id: int,
    data: AssemblyUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    """Update assembly metadata."""
    try:
        return BOMService.update_assembly(db, assembly_id, data.dict(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Parts CRUD
# ---------------------------------------------------------------------------

@router.post("/assemblies/{assembly_id}/parts", response_model=AssemblyPartOut)
def add_part(
    assembly_id: int,
    data: AssemblyPartCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    """Add a part to an assembly."""
    try:
        return BOMService.add_part(db, assembly_id, data.dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/parts/{part_id}", response_model=AssemblyPartOut)
def update_part(
    part_id: int,
    data: AssemblyPartUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    """Update a part."""
    try:
        return BOMService.update_part(db, part_id, data.dict(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/parts/{part_id}")
def delete_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    """Delete a part from an assembly."""
    try:
        BOMService.delete_part(db, part_id)
        return {"message": "Part deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Material Requirements
# ---------------------------------------------------------------------------

@router.post("/assemblies/{assembly_id}/calculate-materials", response_model=list[MaterialRequirementOut])
def calculate_materials(
    assembly_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    """Auto-calculate material requirements from parts."""
    try:
        return BOMService.calculate_material_requirements(db, assembly_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assemblies/{assembly_id}/requirements", response_model=list[MaterialRequirementOut])
def get_requirements(
    assembly_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """View material requirements for an assembly."""
    return BOMService.get_requirements(db, assembly_id)


# ---------------------------------------------------------------------------
# CSV/Excel Import
# ---------------------------------------------------------------------------

@router.post("/import-csv/{customer_id}", response_model=CSVImportResult)
async def import_csv(
    customer_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    """Import assemblies + parts from a CSV file."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    content = await file.read()

    # Try multiple encodings
    df = None
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            df = pd.read_csv(io.BytesIO(content), encoding=encoding)
            break
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue

    if df is None:
        raise HTTPException(status_code=400, detail="Could not parse CSV file")

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    rows = df.where(df.notnull(), None).to_dict(orient="records")

    result = BOMService.import_from_rows(db, customer_id, rows)
    return CSVImportResult(**result)


@router.post("/import-excel/{customer_id}", response_model=CSVImportResult)
async def import_excel(
    customer_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    """Import assemblies + parts from an Excel file."""
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="File must be .xlsx or .xls")

    content = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse Excel file: {e}")

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    rows = df.where(df.notnull(), None).to_dict(orient="records")

    result = BOMService.import_from_rows(db, customer_id, rows)
    return CSVImportResult(**result)


# ---------------------------------------------------------------------------
# Per-Piece Completion Tracking (Phase 3)
# ---------------------------------------------------------------------------

@router.put("/parts/{part_id}/completion")
def update_part_completion(
    part_id: int,
    data: PieceCompletionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    """Update piece completion count for a part."""
    try:
        return StageService.update_part_completion(
            db, part_id, data.completed_delta, current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/assemblies/{assembly_id}/stages/{stage}/pieces")
def update_stage_pieces(
    assembly_id: int,
    stage: str,
    data: PieceCompletionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role("Boss", "Software Supervisor")),
):
    """Batch update piece count for an assembly stage."""
    try:
        return StageService.update_piece_count(
            db, assembly_id, stage, data.completed_delta, current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assemblies/{assembly_id}/progress")
def get_assembly_progress(
    assembly_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get per-stage piece progress for an assembly."""
    try:
        return StageService.get_assembly_progress(db, assembly_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/progress-dashboard")
def get_progress_dashboard(
    customer_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Dashboard aggregate: pieces across all assemblies per stage."""
    return StageService.get_progress_dashboard(db, customer_id)


# ---------------------------------------------------------------------------
# CSV Template Downloads
# ---------------------------------------------------------------------------

@router.get("/templates/csv")
def download_combined_template(
    current_user: models.User = Depends(get_current_user),
):
    """Download sample combined BOM CSV template."""
    return csv_template_service.bom_combined_template()


@router.get("/templates/assemblies-csv")
def download_assemblies_template(
    current_user: models.User = Depends(get_current_user),
):
    """Download sample assemblies CSV template."""
    return csv_template_service.bom_assemblies_template()


@router.get("/templates/parts-csv")
def download_parts_template(
    current_user: models.User = Depends(get_current_user),
):
    """Download sample parts CSV template."""
    return csv_template_service.bom_parts_template()
