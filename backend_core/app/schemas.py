from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "User"


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    username: str
    password: str
    role: str


class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    username: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class CustomerCreate(BaseModel):
    name: str
    project_details: Optional[str]


class ProductionItemCreate(BaseModel):
    item_code: str
    item_name: str
    section: Optional[str]
    length_mm: Optional[int]
    quantity: Optional[float] = 1.0
    unit: Optional[str] = None
    weight_per_unit: Optional[float] = None
    material_requirements: Optional[str] = None  # JSON string
    checklist: Optional[str] = None  # JSON string
    notes: Optional[str] = None


class ProductionItemOut(BaseModel):
    id: int
    customer_id: int
    item_code: str
    item_name: str
    section: Optional[str]
    length_mm: Optional[int]
    quantity: Optional[float] = 1.0
    unit: Optional[str] = None
    weight_per_unit: Optional[float] = None
    material_requirements: Optional[str] = None
    checklist: Optional[str] = None
    notes: Optional[str] = None
    fabrication_deducted: Optional[bool] = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CustomerOut(BaseModel):
    id: int
    name: str
    project_details: Optional[str]
    created_at: datetime
    production_items: Optional[List[ProductionItemOut]] = []

    class Config:
        from_attributes = True


class StageAction(BaseModel):
    production_item_id: int
    stage: str


class ProductionItemWithStages(BaseModel):
    id: int
    customer_id: int
    item_code: str
    item_name: str
    section: Optional[str]
    length_mm: Optional[int]
    quantity: Optional[float] = 1.0
    unit: Optional[str] = None
    weight_per_unit: Optional[float] = None
    material_requirements: Optional[str] = None
    checklist: Optional[str] = None
    notes: Optional[str] = None
    fabrication_deducted: Optional[bool] = False
    stages: List["StageStatusOut"] = []

    class Config:
        from_attributes = True


# Schema for updating a production item (edit functionality)
class ProductionItemUpdate(BaseModel):
    item_code: Optional[str] = None
    item_name: Optional[str] = None
    section: Optional[str] = None
    length_mm: Optional[int] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    weight_per_unit: Optional[float] = None
    material_requirements: Optional[str] = None
    checklist: Optional[str] = None
    notes: Optional[str] = None


# Schema for Excel import with flexible column mapping
class ExcelImportConfig(BaseModel):
    customer_id: int
    sheet_name: Optional[str] = None
    column_mapping: Optional[dict] = None  # Maps Excel columns to ProductionItem fields
    # Default mapping if not provided:
    # {"Item Code": "item_code", "Item Name": "item_name", "Section": "section", etc.}


# Schema for dashboard summary
class DashboardSummary(BaseModel):
    total_raw_materials: int
    total_inventory_value: float
    low_stock_items: int
    fabrication_jobs: int
    painting_jobs: int
    dispatch_jobs: int
    completed_jobs: int
    pending_jobs: int
    recent_activity: List[dict] = []


class MaterialUsageCreate(BaseModel):
    production_item_id: Optional[int]
    name: str
    qty: int
    unit: Optional[str]
    by: Optional[str]


class MaterialUsageOut(BaseModel):
    id: int
    customer_id: int
    production_item_id: Optional[int]
    name: str
    qty: int
    unit: Optional[str]
    by: Optional[str]
    ts: datetime

    class Config:
        from_attributes = True


class CustomerTrackingOut(BaseModel):
    id: int
    name: str
    project: Optional[str]
    current_stage: Optional[str]
    production_items: List[ProductionItemWithStages] = []
    material_usage: List[MaterialUsageOut] = []
    stage_history: List["StageStatusOut"] = []

    class Config:
        from_attributes = True


class StageStatusOut(BaseModel):
    id: int
    production_item_id: int
    stage: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    updated_by: Optional[int]

    class Config:
        from_attributes = True


class QueryCreate(BaseModel):
    customer_id: int
    production_item_id: Optional[int]
    stage: Optional[str]
    description: str
    image_path: Optional[str]


class QueryOut(BaseModel):
    id: int
    customer_id: int
    production_item_id: Optional[int]
    stage: Optional[str]
    description: str
    image_path: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class InstructionCreate(BaseModel):
    message: str


class InstructionOut(BaseModel):
    id: int
    message: str
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class InventoryIn(BaseModel):
    name: str
    unit: str | None = None
    total: int = 0
    used: int = 0
    code: str | None = None
    section: str | None = None
    category: str | None = None


class InventoryOut(BaseModel):
    id: int
    name: str
    unit: str | None = None
    total: int
    used: int
    code: str | None = None
    section: str | None = None
    category: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class NotificationOut(BaseModel):
    id: int
    user_id: int | None = None
    role: str | None = None
    message: str
    level: str
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationCreate(BaseModel):
    user_id: int | None = None
    role: str | None = None
    message: str
    level: str = "info"


class NotificationSettingOut(BaseModel):
    in_app: bool = True
    email: bool = False
    push: bool = False
    instr_from_boss: bool = True
    stage_changes: bool = True
    query_raised: bool = True
    query_response: bool = True
    low_inventory: bool = True
    dispatch_completed: bool = True
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class NotificationSettingIn(BaseModel):
    in_app: bool | None = None
    email: bool | None = None
    push: bool | None = None
    instr_from_boss: bool | None = None
    stage_changes: bool | None = None
    query_raised: bool | None = None
    query_response: bool | None = None
    low_inventory: bool | None = None
    dispatch_completed: bool | None = None


class RoleNotificationSettingOut(NotificationSettingOut):
    role: str


class RoleNotificationSettingIn(NotificationSettingIn):
    pass


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str

