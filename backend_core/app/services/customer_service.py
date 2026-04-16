from typing import Optional
from sqlalchemy.orm import Session
import json

from .. import models

try:
    from .. import models_v2
except Exception:
    models_v2 = None


def hard_delete_customer(db: Session, customer: models.Customer, user: Optional[models.User] = None):
    """Permanently delete a customer and all related data in a safe order.

    This function performs application-level deletes to avoid leaving orphaned rows.
    It commits the transaction when successful; raises on failure.
    """
    customer_id = customer.id

    # Collect related production items
    items = db.query(models.ProductionItem).filter(models.ProductionItem.customer_id == customer_id).all()
    item_ids = [it.id for it in items]

    try:
        # Stage tracking
        if item_ids:
            db.query(models.StageTracking).filter(models.StageTracking.production_item_id.in_(item_ids)).delete(synchronize_session=False)

            # Material usage
            if hasattr(models, 'MaterialUsage'):
                db.query(models.MaterialUsage).filter(models.MaterialUsage.production_item_id.in_(item_ids)).delete(synchronize_session=False)

            # Material consumption (if any relation)
            if hasattr(models, 'MaterialConsumption'):
                # Some codebases link consumption to material_usage; we handle both defensively
                try:
                    db.query(models.MaterialConsumption).filter(models.MaterialConsumption.material_usage_id.in_(item_ids)).delete(synchronize_session=False)
                except Exception:
                    pass

            # Scrap and reusable stock
            if hasattr(models, 'ScrapRecord'):
                db.query(models.ScrapRecord).filter(models.ScrapRecord.source_item_id.in_(item_ids)).delete(synchronize_session=False)
            if hasattr(models, 'ReusableStock'):
                db.query(models.ReusableStock).filter(models.ReusableStock.source_item_id.in_(item_ids)).delete(synchronize_session=False)

            # Tracking history
            if hasattr(models, 'TrackingStageHistory'):
                db.query(models.TrackingStageHistory).filter(models.TrackingStageHistory.material_id.in_(item_ids)).delete(synchronize_session=False)

            # Capture ExcelUpload ids referenced
            excel_rows = db.query(models.ProductionItem.excel_upload_id).filter(models.ProductionItem.id.in_(item_ids)).distinct().all()
            excel_ids = [e[0] for e in excel_rows if e and e[0]]

            # Delete production items
            db.query(models.ProductionItem).filter(models.ProductionItem.id.in_(item_ids)).delete(synchronize_session=False)

            # Delete ExcelUpload records referenced by these items
            if excel_ids:
                db.query(models.ExcelUpload).filter(models.ExcelUpload.id.in_(excel_ids)).delete(synchronize_session=False)

        # Finally delete the customer record
        db.query(models.Customer).filter(models.Customer.id == customer_id).delete(synchronize_session=False)

        # Optional audit log (models_v2.AuditLog) - write a clear HARD_DELETE entry
        if models_v2 is not None and hasattr(models_v2, 'AuditLog') and user is not None:
            try:
                meta = { 'customer_name': getattr(customer, 'name', None) }
                log = models_v2.AuditLog(
                    entity_type='Customer',
                    entity_id=customer_id,
                    action='HARD_DELETE_CUSTOMER',
                    old_values=json.dumps(meta),
                    new_values=None,
                    user_id=getattr(user, 'id', None)
                )
                db.add(log)
            except Exception:
                pass

        db.commit()
    except Exception:
        db.rollback()
        raise
