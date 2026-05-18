"""
System Settings API Router
===========================
Admin-level endpoints for managing company profile, naming series,
workflow configurations, and system key-value settings.

Write endpoints (PUT) are restricted to the Boss role.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..deps import boss_only, get_current_user, get_db
from ..models_v2 import NumberSequence, SystemConfig
from ..models_v3 import StageConfig

router = APIRouter(prefix="/api/v2/settings", tags=["Settings"])


# =============================================================================
# SCHEMAS
# =============================================================================


class CompanyProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    company_gstin: Optional[str] = None
    company_phone: Optional[str] = None
    company_email: Optional[str] = None
    company_logo_url: Optional[str] = None


class NamingSeriesUpdate(BaseModel):
    format_str: str = Field(..., min_length=1, max_length=100)


class SystemConfigUpdate(BaseModel):
    value: str


# =============================================================================
# COMPANY PROFILE
# =============================================================================

COMPANY_KEYS = [
    "company_name",
    "company_address",
    "company_gstin",
    "company_phone",
    "company_email",
    "company_logo_url",
]


@router.get("/company")
def get_company_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get company profile from system_config."""
    rows = db.query(SystemConfig).filter(SystemConfig.key.in_(COMPANY_KEYS)).all()
    result: Dict[str, Any] = {k: None for k in COMPANY_KEYS}
    for row in rows:
        result[row.key] = row.value
    return result


@router.put("/company")
def update_company_settings(
    payload: CompanyProfileUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(boss_only),
):
    """Update company profile. Boss only."""
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided to update",
        )

    for key, value in updates.items():
        row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if row:
            row.value = value
            row.updated_by = current_user.id
        else:
            row = SystemConfig(
                key=key,
                value=value,
                description=f"Company profile: {key}",
                updated_by=current_user.id,
            )
            db.add(row)

    db.commit()
    return {"success": True, "updated": list(updates.keys())}


# =============================================================================
# NAMING SERIES
# =============================================================================


@router.get("/naming-series")
def get_naming_series(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all number sequences with their formats."""
    sequences = db.query(NumberSequence).all()
    return [
        {
            "id": seq.id,
            "sequence_name": seq.sequence_name,
            "prefix": seq.prefix,
            "current_number": seq.current_number,
            "year": seq.year,
            "padding": seq.padding,
            "format_str": seq.format_str,
        }
        for seq in sequences
    ]


@router.put("/naming-series/{sequence_name}")
def update_naming_series(
    sequence_name: str,
    payload: NamingSeriesUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(boss_only),
):
    """Update format_str for a naming series. Boss only."""
    seq = db.query(NumberSequence).filter(NumberSequence.sequence_name == sequence_name).first()
    if not seq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Naming series '{sequence_name}' not found",
        )

    seq.format_str = payload.format_str
    db.commit()
    return {
        "success": True,
        "sequence_name": sequence_name,
        "format_str": seq.format_str,
    }


# =============================================================================
# WORKFLOW CONFIGS
# =============================================================================


@router.get("/workflows")
def get_workflow_configs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List stage configs from v3_stage_configs."""
    configs = db.query(StageConfig).order_by(StageConfig.sequence.asc()).all()
    return [
        {
            "id": cfg.id,
            "customer_id": cfg.customer_id,
            "stage_name": cfg.stage_name,
            "sequence": cfg.sequence,
            "is_mandatory": cfg.is_mandatory,
            "requires_qa_hold": cfg.requires_qa_hold,
            "auto_deduct_material": cfg.auto_deduct_material,
        }
        for cfg in configs
    ]


# =============================================================================
# SYSTEM CONFIG (generic key-value)
# =============================================================================


@router.get("/system")
def get_system_config(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get all system_config key-value pairs."""
    rows = db.query(SystemConfig).all()
    return [
        {
            "id": row.id,
            "key": row.key,
            "value": row.value,
            "description": row.description,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        for row in rows
    ]


@router.put("/system/{key}")
def update_system_config(
    key: str,
    payload: SystemConfigUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(boss_only),
):
    """Update a system config value. Boss only."""
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not row:
        # Create if not exists
        row = SystemConfig(
            key=key,
            value=payload.value,
            updated_by=current_user.id,
        )
        db.add(row)
    else:
        row.value = payload.value
        row.updated_by = current_user.id

    db.commit()
    return {
        "success": True,
        "key": key,
        "value": row.value,
    }
