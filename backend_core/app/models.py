from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.orm import relationship
from .db import Base
from sqlalchemy.sql import func




class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    #STRICT ROLE CONTROL
    role = Column(
        String,
        nullable=False,
        default="user"  # default safe role
    )

    company = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    @property
    def password_hash(self):
        return self.hashed_password

    @password_hash.setter
    def password_hash(self, value):
        self.hashed_password = value


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    project_details = Column(Text)
    email = Column(String, nullable=True, index=True)
    phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    # Order-level status: ACTIVE | COMPLETED | ARCHIVED
    order_status = Column(String, default="ACTIVE")
    # Soft-delete flag for customers (do NOT hard delete customers)
    is_deleted = Column(Boolean, default=False)
    production_items = relationship("ProductionItem", back_populates="customer")


class ProductionItem(Base):
    __tablename__ = "production_items"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    item_code = Column(String, nullable=False)
    item_name = Column(String, nullable=False)
    section = Column(String, nullable=True)
    length_mm = Column(Integer, nullable=True)
    quantity = Column(Float, nullable=True, default=1.0)  # Quantity from Excel
    unit = Column(String, nullable=True)  # Unit from Excel
    weight_per_unit = Column(Float, nullable=True)  # Weight per unit for material calculation
    # Material requirements for this item (JSON stored as string for SQLite compatibility)
    material_requirements = Column(Text, nullable=True)  # JSON: [{"material_id": 1, "qty": 10.5}, ...]
    # Checklist for tracking progress
    checklist = Column(Text, nullable=True)  # JSON: [{"item": "Cut", "done": true}, ...]
    # Notes for the item
    notes = Column(Text, nullable=True)
    # Current stage tracking for this production item (lowercase values)
    current_stage = Column(String, nullable=False, default="fabrication")
    stage_updated_at = Column(DateTime, nullable=True)
    stage_updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    # Flag to track if fabrication deduction has been done (prevents double deduction)
    fabrication_deducted = Column(Boolean, default=False)
    # Also use material_deducted as an alias for FIFO deduction tracking
    material_deducted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    customer = relationship("Customer", back_populates="production_items")
    stages = relationship("StageTracking", back_populates="production_item")
    is_completed = Column(Boolean, default=False)
    # Soft-archive flag for completed items. Additive change, safe default False.
    is_archived = Column(Boolean, default=False)
    # Parent link for split items (nullable). Additive, safe.
    parent_item_id = Column(Integer, ForeignKey("production_items.id"), nullable=True)
    # Optional link to originating Excel upload (nullable)
    excel_upload_id = Column(Integer, ForeignKey("excel_uploads.id"), nullable=True)
    FINAL_STAGE = "dispatch"



class StageTracking(Base):
    __tablename__ = "stage_tracking"
    id = Column(Integer, primary_key=True, index=True)
    production_item_id = Column(Integer, ForeignKey("production_items.id"), nullable=False)
    stage = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_checked = Column(Boolean, default=False)
    production_item = relationship("ProductionItem", back_populates="stages")


class Query(Base):
    __tablename__ = "queries"
    id = Column(Integer, primary_key=True, index=True)
    # Backwards-compatible fields (existing application data)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    production_item_id = Column(Integer, ForeignKey("production_items.id"), nullable=True)
    stage = Column(String, nullable=True)
    # New fields for user-facing queries
    title = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    # Keep legacy description/image_path for compatibility
    description = Column(Text, nullable=True)
    image_path = Column(String, nullable=True)

    # Who created the query (users.id)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    status = Column(
        String,
        default="OPEN",  # OPEN | IN_PROGRESS | CLOSED
        nullable=False
    )

    admin_reply = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


class Instruction(Base):
    __tablename__ = "instructions"
    id = Column(Integer, primary_key=True, index=True)
    message = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)


class MaterialUsage(Base):
    __tablename__ = "material_usage"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    production_item_id = Column(Integer, ForeignKey("production_items.id"), nullable=True)
    name = Column(String, nullable=False)
    qty = Column(Float, nullable=False)  # Changed to Float for decimal quantities
    unit = Column(String, nullable=True)
    by = Column(String, nullable=True)
    applied = Column(Boolean, default=False)  # Whether this usage has been applied to inventory
    ts = Column(DateTime, default=datetime.utcnow)


class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    unit = Column(String, nullable=True)
    total = Column(Float, nullable=False, default=0.0)  # Changed to Float for decimal quantities
    used = Column(Float, nullable=False, default=0.0)   # Changed to Float for decimal quantities
    # Optional metadata fields to support richer searching/filtering
    code = Column(String, nullable=True)
    section = Column(String, nullable=True)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    role = Column(String, nullable=True)  # target role (optional)
    message = Column(Text, nullable=False)
    # Backwards-compatible title property (no DB column) - derived from message
    @property
    def title(self):
        if self.message:
            return (self.message[:100] + "...") if len(self.message) > 100 else self.message
        return ""
    level = Column(String, nullable=False, default="info")
    category = Column(String, nullable=True) # e.g. "stage_changes", "instr_from_boss"
    read = Column(Boolean, default=False)

    @property
    def is_read(self):
        return bool(self.read)
    created_at = Column(DateTime, default=datetime.utcnow)


class ActivityLog(Base):
    """
    Generic activity log for system-wide events (e.g., inventory resets).
    """
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False) # e.g. "RESET_CONSUMED"
    description = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class NotificationSetting(Base):
    __tablename__ = "notification_settings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    in_app = Column(Boolean, default=True)
    email = Column(Boolean, default=False)
    push = Column(Boolean, default=False)
    # Per-event toggles
    instr_from_boss = Column(Boolean, default=True)
    stage_changes = Column(Boolean, default=True)
    query_raised = Column(Boolean, default=True)
    query_response = Column(Boolean, default=True)
    low_inventory = Column(Boolean, default=True)
    dispatch_completed = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ExcelUpload(Base):
    __tablename__ = "excel_uploads"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)


class MaterialConsumption(Base):
    __tablename__ = "material_consumption"
    id = Column(Integer, primary_key=True, index=True)
    material_usage_id = Column(Integer, ForeignKey("material_usage.id"), nullable=False)
    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=False)
    qty = Column(Float, nullable=False)
    ts = Column(DateTime, default=datetime.utcnow)


class TrackingStageHistory(Base):
    __tablename__ = "tracking_stage_history"
    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("production_items.id"), nullable=False)
    from_stage = Column(String, nullable=True)
    to_stage = Column(String, nullable=True)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow)
    remarks = Column(Text, nullable=True)


class RoleNotificationSetting(Base):
    __tablename__ = "role_notification_settings"
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, unique=True, nullable=False)
    in_app = Column(Boolean, default=True)
    email = Column(Boolean, default=False)
    push = Column(Boolean, default=False)
    # Per-event toggles for role defaults
    instr_from_boss = Column(Boolean, default=True)
    stage_changes = Column(Boolean, default=True)
    query_raised = Column(Boolean, default=True)
    query_response = Column(Boolean, default=True)
    low_inventory = Column(Boolean, default=True)
    dispatch_completed = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ScrapRecord(Base):
    """Track scrap/waste materials after dispatch"""
    __tablename__ = "scrap_records"
    id = Column(Integer, primary_key=True, index=True)
    material_name = Column(String, nullable=False)
    weight_kg = Column(Float, nullable=False)
    length_mm = Column(Float, nullable=True)  # Dimension for matching
    width_mm = Column(Float, nullable=True)
    quantity = Column(Integer, default=1)  # Number of pieces
    reason_code = Column(String, nullable=False)  # cutting_waste, defect, damage, overrun, leftover
    source_item_id = Column(Integer, ForeignKey("production_items.id"), nullable=True)
    source_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    dimensions = Column(String, nullable=True)  # Text description e.g., "200mm x 50mm x 6m"
    notes = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, returned_to_inventory, disposed, recycled, sold
    scrap_value = Column(Float, nullable=True)  # Sale value if sold
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ReusableStock(Base):
    """Track reusable offcuts and leftover pieces that can be used again"""
    __tablename__ = "reusable_stock"
    id = Column(Integer, primary_key=True, index=True)
    material_name = Column(String, nullable=False)
    length_mm = Column(Float, nullable=True)  # For dimension matching
    width_mm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=False)
    quantity = Column(Integer, default=1)  # Number of pieces
    dimensions = Column(String, nullable=False)  # Text e.g., "1200mm x 150mm beam"
    source_item_id = Column(Integer, ForeignKey("production_items.id"), nullable=True)
    source_customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    quality_grade = Column(String, default="A")  # A=good, B=minor defects, C=usable with caution
    notes = Column(Text, nullable=True)
    is_available = Column(Boolean, default=True)
    used_in_item_id = Column(Integer, ForeignKey("production_items.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MaterialMapping(Base):
    """Link Excel product/profile names to specific inventory materials"""
    __tablename__ = "material_mappings"
    id = Column(Integer, primary_key=True, index=True)
    excel_name = Column(String, unique=True, nullable=False, index=True)
    material_id = Column(Integer, ForeignKey("inventory.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to Inventory
    material = relationship("Inventory")

