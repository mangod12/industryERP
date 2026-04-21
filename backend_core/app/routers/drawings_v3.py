from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user, boss_or_supervisor
from ..models import User, Inventory
from ..models_v2 import StockLot, StockMovement, MovementType, QAStatus
from ..models_v3 import (
    Assembly,
    Component,
    ComponentInstance,
    ComponentStageStatus,
    Drawing,
    DrawingStatus,
    MaterialReservation,
    ReservationStatus,
)
from ..services.component_tracking_service import ComponentTrackingService
from ..services.drawing_service import DrawingService
from ..services.inventory_service import StockLotService, get_next_sequence
from ..schemas_v3 import (
    DrawingCreate,
    DrawingUpdate,
    DrawingOut,
    DrawingSummary,
    AssemblyCreate,
    AssemblyOut,
    ComponentCreate,
    ComponentOut,
    ComponentInstanceOut,
    AdvanceStageRequest,
    BatchAdvanceRequest,
    AdvanceStageResponse,
    KanbanBoard,
    DrawingProgress,
    ReserveMaterialsRequest,
    IssueMaterialRequest,
    MaterialReservationOut,
)
from ..schemas_v3 import AssemblyUpdate, ComponentUpdate, ReturnMaterialRequest


router = APIRouter(prefix="/api/v3/drawings", tags=["drawings-v3"])


class ReasonRequest(BaseModel):
    reason: str


def _decimal(value: Decimal | float | int | None) -> float:
    return float(value or 0)


def _handle_value_error(exc: ValueError) -> None:
    detail = str(exc)
    if "not found" in detail.lower():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _get_drawing_or_404(db: Session, drawing_id: int) -> Drawing:
    drawing = db.query(Drawing).filter(Drawing.id == drawing_id).first()
    if not drawing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drawing not found")
    return drawing


def _get_assembly_or_404(db: Session, assembly_id: int) -> Assembly:
    assembly = db.query(Assembly).filter(Assembly.id == assembly_id).first()
    if not assembly:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assembly not found")
    return assembly


def _get_component_or_404(db: Session, component_id: int) -> Component:
    component = db.query(Component).filter(Component.id == component_id).first()
    if not component:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component not found")
    return component


def _get_instance_or_404(db: Session, instance_id: int) -> ComponentInstance:
    instance = db.query(ComponentInstance).filter(ComponentInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Component instance not found")
    return instance


def _serialize_instance(instance: ComponentInstance) -> ComponentInstanceOut:
    return ComponentInstanceOut(
        id=instance.id,
        instance_number=instance.instance_number,
        serial_tag=instance.serial_tag,
        current_stage=instance.current_stage,
        stage_status=instance.stage_status,
        stage_updated_at=instance.stage_updated_at,
        is_completed=instance.is_completed,
        is_scrapped=instance.is_scrapped,
        material_reserved=instance.material_reserved,
        material_issued=instance.material_issued,
        material_consumed=instance.material_consumed,
        stock_lot_id=instance.stock_lot_id,
        heat_number=instance.heat_number,
    )


def _serialize_component(component: Component) -> ComponentOut:
    instances = component.instances or []
    completed = sum(1 for inst in instances if inst.is_completed)
    in_progress = sum(
        1 for inst in instances if inst.stage_status == ComponentStageStatus.IN_PROGRESS
    )
    return ComponentOut(
        id=component.id,
        assembly_id=component.assembly_id,
        piece_mark=component.piece_mark,
        profile_section=component.profile_section,
        grade=component.grade,
        length_mm=_decimal(component.length_mm) if component.length_mm is not None else None,
        width_mm=_decimal(component.width_mm) if component.width_mm is not None else None,
        thickness_mm=_decimal(component.thickness_mm) if component.thickness_mm is not None else None,
        quantity_per_assembly=component.quantity_per_assembly,
        weight_each_kg=_decimal(component.weight_each_kg),
        material_id=component.material_id,
        inventory_id=component.inventory_id,
        notes=component.notes,
        created_at=component.created_at,
        updated_at=component.updated_at,
        instance_count=len(instances),
        instances_completed=completed,
        instances_in_progress=in_progress,
    )


def _serialize_assembly(assembly: Assembly) -> AssemblyOut:
    return AssemblyOut(
        id=assembly.id,
        drawing_id=assembly.drawing_id,
        mark_number=assembly.mark_number,
        description=assembly.description,
        quantity_required=assembly.quantity_required,
        quantity_complete=assembly.quantity_complete,
        total_weight_kg=_decimal(assembly.total_weight_kg),
        notes=assembly.notes,
        created_at=assembly.created_at,
        updated_at=assembly.updated_at,
        components=[_serialize_component(component) for component in assembly.components],
    )


def _serialize_drawing(drawing: Drawing) -> DrawingOut:
    assemblies = [_serialize_assembly(assembly) for assembly in drawing.assemblies]
    components = [component for assembly in drawing.assemblies for component in assembly.components]
    instances = [instance for component in components for instance in component.instances]
    completed_instances = sum(1 for instance in instances if instance.is_completed)
    completion_pct = (completed_instances / len(instances) * 100) if instances else 0.0

    return DrawingOut(
        id=drawing.id,
        drawing_number=drawing.drawing_number,
        revision=drawing.revision,
        title=drawing.title,
        customer_id=drawing.customer_id,
        project_ref=drawing.project_ref,
        status=drawing.status,
        total_weight_kg=_decimal(drawing.total_weight_kg),
        completed_weight_kg=_decimal(drawing.completed_weight_kg),
        released_date=drawing.released_date,
        released_by=drawing.released_by,
        created_by=drawing.created_by,
        notes=drawing.notes,
        created_at=drawing.created_at,
        updated_at=drawing.updated_at,
        assemblies=assemblies,
        component_count=len(components),
        instance_count=len(instances),
        completed_instance_count=completed_instances,
        completion_pct=round(completion_pct, 2),
    )


def _serialize_summary(drawing: Drawing) -> DrawingSummary:
    components = [component for assembly in drawing.assemblies for component in assembly.components]
    total_instances = sum(len(component.instances) for component in components)
    completed_instances = sum(
        1 for component in components for instance in component.instances if instance.is_completed
    )
    completion_pct = (completed_instances / total_instances * 100) if total_instances else 0.0
    return DrawingSummary(
        id=drawing.id,
        drawing_number=drawing.drawing_number,
        revision=drawing.revision,
        title=drawing.title,
        status=drawing.status,
        total_weight_kg=_decimal(drawing.total_weight_kg),
        completed_weight_kg=_decimal(drawing.completed_weight_kg),
        customer_name=drawing.customer.name if drawing.customer else "",
        project_ref=drawing.project_ref,
        component_count=len(components),
        completion_pct=round(completion_pct, 2),
    )


def _serialize_reservation(reservation: MaterialReservation) -> MaterialReservationOut:
    return MaterialReservationOut(
        id=reservation.id,
        component_instance_id=reservation.component_instance_id,
        stock_lot_id=reservation.stock_lot_id,
        reserved_weight_kg=_decimal(reservation.reserved_weight_kg),
        issued_weight_kg=_decimal(reservation.issued_weight_kg),
        consumed_weight_kg=_decimal(reservation.consumed_weight_kg),
        status=reservation.status,
        reserved_at=reservation.reserved_at,
    )


def _recalculate_after_structure_change(db: Session, drawing_id: int) -> None:
    DrawingService._recalculate_weights(db, drawing_id)
    DrawingService.update_drawing_status(db, drawing_id)


@router.post("", response_model=DrawingOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=DrawingOut, status_code=status.HTTP_201_CREATED)
async def create_drawing(
    data: DrawingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        drawing = DrawingService.create_drawing(
            db=db,
            drawing_number=data.drawing_number,
            title=data.title,
            customer_id=data.customer_id,
            project_ref=data.project_ref,
            notes=data.notes,
            created_by=current_user.id,
        )
        db.commit()
        db.refresh(drawing)
        return _serialize_drawing(drawing)
    except ValueError as exc:
        db.rollback()
        _handle_value_error(exc)


@router.get("", response_model=list[DrawingSummary], status_code=status.HTTP_200_OK)
@router.get("/", response_model=list[DrawingSummary], status_code=status.HTTP_200_OK)
async def list_drawings(
    customer_id: int | None = Query(None),
    status_filter: DrawingStatus | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        drawings = DrawingService.list_drawings(
            db=db,
            customer_id=customer_id,
            status=status_filter,
            skip=skip,
            limit=limit,
        )
        return [_serialize_summary(drawing) for drawing in drawings]
    except ValueError as exc:
        _handle_value_error(exc)


@router.get("/kanban", response_model=KanbanBoard, status_code=status.HTTP_200_OK)
async def get_kanban(
    drawing_id: int | None = Query(None),
    customer_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        customer_scope = customer_id
        if drawing_id:
            drawing = _get_drawing_or_404(db, drawing_id)
            customer_scope = drawing.customer_id

        pipeline = DrawingService.get_stage_pipeline(db, customer_scope)
        query = (
            db.query(ComponentInstance)
            .join(Component, ComponentInstance.component_id == Component.id)
            .join(Assembly, Component.assembly_id == Assembly.id)
            .join(Drawing, Assembly.drawing_id == Drawing.id)
            .filter(
                ComponentInstance.is_scrapped == False,
                ComponentInstance.is_completed == False,
            )
        )
        if drawing_id is not None:
            query = query.filter(Drawing.id == drawing_id)
        if customer_id is not None:
            query = query.filter(Drawing.customer_id == customer_id)

        stage_map: dict[str, list[ComponentInstanceOut]] = {}
        for instance in query.all():
            stage_map.setdefault(instance.current_stage, []).append(_serialize_instance(instance))

        columns = []
        for stage in pipeline:
            stage_name = stage["stage_name"]
            instances = stage_map.get(stage_name, [])
            columns.append(
                {
                    "stage_name": stage_name,
                    "count": len(instances),
                    "instances": instances,
                }
            )

        extra_stages = sorted(set(stage_map.keys()) - {stage["stage_name"] for stage in pipeline})
        for stage_name in extra_stages:
            instances = stage_map[stage_name]
            columns.append(
                {
                    "stage_name": stage_name,
                    "count": len(instances),
                    "instances": instances,
                }
            )

        return KanbanBoard(drawing_id=drawing_id, columns=columns)
    except ValueError as exc:
        _handle_value_error(exc)


@router.get("/{drawing_id}", response_model=DrawingOut, status_code=status.HTTP_200_OK)
async def get_drawing(
    drawing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        _ = DrawingService.get_drawing_detail(db, drawing_id)
        drawing = _get_drawing_or_404(db, drawing_id)
        return _serialize_drawing(drawing)
    except ValueError as exc:
        _handle_value_error(exc)


@router.put("/{drawing_id}", response_model=DrawingOut, status_code=status.HTTP_200_OK)
async def update_drawing(
    drawing_id: int,
    data: DrawingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    drawing = _get_drawing_or_404(db, drawing_id)
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(drawing, field, value)

    drawing.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(drawing)
    return _serialize_drawing(drawing)


@router.post("/{drawing_id}/release", response_model=DrawingOut, status_code=status.HTTP_200_OK)
async def release_drawing(
    drawing_id: int,
    current_user: User = Depends(boss_or_supervisor),
    db: Session = Depends(get_db),
):
    try:
        drawing = DrawingService.release_drawing(db, drawing_id, current_user.id)
        db.commit()
        db.refresh(drawing)
        return _serialize_drawing(drawing)
    except ValueError as exc:
        db.rollback()
        _handle_value_error(exc)


@router.post(
    "/{drawing_id}/assemblies",
    response_model=AssemblyOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_assembly(
    drawing_id: int,
    data: AssemblyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        assembly = DrawingService.add_assembly(
            db=db,
            drawing_id=drawing_id,
            mark_number=data.mark_number,
            description=data.description,
            quantity_required=data.quantity_required,
            notes=data.notes,
        )
        db.commit()
        db.refresh(assembly)
        return _serialize_assembly(assembly)
    except ValueError as exc:
        db.rollback()
        _handle_value_error(exc)


@router.put("/assemblies/{assembly_id}", response_model=AssemblyOut, status_code=status.HTTP_200_OK)
async def update_assembly(
    assembly_id: int,
    data: AssemblyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assembly = _get_assembly_or_404(db, assembly_id)
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(assembly, field, value)

    assembly.updated_at = datetime.utcnow()
    _recalculate_after_structure_change(db, assembly.drawing_id)
    db.commit()
    db.refresh(assembly)
    return _serialize_assembly(assembly)


@router.post(
    "/assemblies/{assembly_id}/components",
    response_model=ComponentOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_component(
    assembly_id: int,
    data: ComponentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        component = DrawingService.add_component(
            db=db,
            assembly_id=assembly_id,
            piece_mark=data.piece_mark,
            profile_section=data.profile_section,
            grade=data.grade,
            length_mm=data.length_mm,
            width_mm=data.width_mm,
            thickness_mm=data.thickness_mm,
            quantity_per_assembly=data.quantity_per_assembly,
            weight_each_kg=data.weight_each_kg,
            material_id=data.material_id,
            inventory_id=data.inventory_id,
            notes=data.notes,
        )
        db.commit()
        db.refresh(component)
        return _serialize_component(component)
    except ValueError as exc:
        db.rollback()
        _handle_value_error(exc)


@router.put("/components/{component_id}", response_model=ComponentOut, status_code=status.HTTP_200_OK)
async def update_component(
    component_id: int,
    data: ComponentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    component = _get_component_or_404(db, component_id)
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(component, field, value)

    component.updated_at = datetime.utcnow()
    _recalculate_after_structure_change(db, component.assembly.drawing_id)
    db.commit()
    db.refresh(component)
    return _serialize_component(component)


@router.delete("/components/{component_id}", status_code=status.HTTP_200_OK)
async def delete_component(
    component_id: int,
    current_user: User = Depends(boss_or_supervisor),
    db: Session = Depends(get_db),
):
    component = _get_component_or_404(db, component_id)
    drawing_id = component.assembly.drawing_id
    db.delete(component)
    db.flush()
    _recalculate_after_structure_change(db, drawing_id)
    db.commit()
    return {"success": True, "message": "Component deleted"}


@router.post(
    "/instances/{instance_id}/advance",
    response_model=AdvanceStageResponse,
    status_code=status.HTTP_200_OK,
)
async def advance_stage(
    instance_id: int,
    data: AdvanceStageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if data.component_instance_id != instance_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Instance ID mismatch")

    try:
        result = ComponentTrackingService.advance_stage(
            db=db,
            instance_id=instance_id,
            user_id=current_user.id,
            target_stage=data.target_stage,
            remarks=data.remarks,
            station=data.station,
        )
        db.commit()
        return AdvanceStageResponse(**result)
    except ValueError as exc:
        db.rollback()
        _handle_value_error(exc)


@router.post("/instances/{instance_id}/start", status_code=status.HTTP_200_OK)
async def start_stage(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = ComponentTrackingService.start_stage(db, instance_id, current_user.id)
        db.commit()
        return result
    except ValueError as exc:
        db.rollback()
        _handle_value_error(exc)


@router.post("/instances/{instance_id}/hold", status_code=status.HTTP_200_OK)
async def hold_stage(
    instance_id: int,
    data: ReasonRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = ComponentTrackingService.hold_stage(db, instance_id, current_user.id, data.reason)
        db.commit()
        return result
    except ValueError as exc:
        db.rollback()
        _handle_value_error(exc)


@router.post("/instances/{instance_id}/scrap", status_code=status.HTTP_200_OK)
async def scrap_instance(
    instance_id: int,
    data: ReasonRequest,
    current_user: User = Depends(boss_or_supervisor),
    db: Session = Depends(get_db),
):
    try:
        result = ComponentTrackingService.scrap_instance(db, instance_id, current_user.id, data.reason)
        db.commit()
        return result
    except ValueError as exc:
        db.rollback()
        _handle_value_error(exc)


@router.post("/instances/batch-advance", status_code=status.HTTP_200_OK)
async def batch_advance(
    data: BatchAdvanceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        results = ComponentTrackingService.batch_advance(
            db=db,
            instance_ids=data.instance_ids,
            user_id=current_user.id,
            target_stage=data.target_stage,
            remarks=data.remarks,
            station=data.station,
        )
        db.commit()
        return results
    except ValueError as exc:
        db.rollback()
        _handle_value_error(exc)


@router.get("/{drawing_id}/material-usage", status_code=status.HTTP_200_OK)
async def get_material_usage(
    drawing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get complete material usage report for a drawing — what items were used, per component."""
    try:
        return DrawingService.get_material_usage(db, drawing_id)
    except ValueError as exc:
        _handle_value_error(exc)


@router.get("/{drawing_id}/progress", response_model=DrawingProgress, status_code=status.HTTP_200_OK)
async def get_progress(
    drawing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    drawing = _get_drawing_or_404(db, drawing_id)
    instances = [
        instance
        for assembly in drawing.assemblies
        for component in assembly.components
        for instance in component.instances
    ]
    stages: dict[str, int] = {}
    for instance in instances:
        stages[instance.current_stage] = stages.get(instance.current_stage, 0) + 1

    total_instances = len(instances)
    completed_instances = sum(1 for instance in instances if instance.is_completed)
    pct_complete = (completed_instances / total_instances * 100) if total_instances else 0.0

    return DrawingProgress(
        drawing_id=drawing.id,
        drawing_number=drawing.drawing_number,
        stages=stages,
        total_instances=total_instances,
        completed_instances=completed_instances,
        pct_complete=round(pct_complete, 2),
    )


@router.post(
    "/{drawing_id}/reserve-materials",
    response_model=list[MaterialReservationOut],
    status_code=status.HTTP_200_OK,
)
async def reserve_materials(
    drawing_id: int,
    data: ReserveMaterialsRequest,
    current_user: User = Depends(boss_or_supervisor),
    db: Session = Depends(get_db),
):
    if data.drawing_id != drawing_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Drawing ID mismatch")

    drawing = _get_drawing_or_404(db, drawing_id)
    reservations: list[MaterialReservation] = []

    try:
        for assembly in drawing.assemblies:
            for component in assembly.components:
                for instance in component.instances:
                    if instance.material_reserved:
                        continue

                    reservation = None
                    if component.material_id:
                        required_weight = Decimal(str(component.weight_each_kg))
                        lot = (
                            db.query(StockLot)
                            .filter(
                                StockLot.material_id == component.material_id,
                                StockLot.is_active == True,
                                StockLot.is_blocked == False,
                                StockLot.qa_status.in_([QAStatus.APPROVED, QAStatus.CONDITIONAL]),
                                StockLot.current_weight_kg >= required_weight,
                            )
                            .order_by(StockLot.received_date.asc())
                            .with_for_update()
                            .first()
                        )
                        if not lot:
                            raise ValueError(
                                f"No eligible stock lot found for instance {instance.id}"
                            )

                        reservation = MaterialReservation(
                            component_instance_id=instance.id,
                            stock_lot_id=lot.id,
                            reserved_weight_kg=required_weight,
                            issued_weight_kg=Decimal("0"),
                            consumed_weight_kg=Decimal("0"),
                            status=ReservationStatus.RESERVED,
                            reserved_by=current_user.id,
                            reserved_at=datetime.utcnow(),
                        )
                    elif component.inventory_id:
                        reservation = MaterialReservation(
                            component_instance_id=instance.id,
                            inventory_id=component.inventory_id,
                            reserved_weight_kg=Decimal(str(component.weight_each_kg)),
                            issued_weight_kg=Decimal("0"),
                            consumed_weight_kg=Decimal("0"),
                            status=ReservationStatus.RESERVED,
                            reserved_by=current_user.id,
                            reserved_at=datetime.utcnow(),
                        )
                    else:
                        raise ValueError(
                            f"Component {component.id} has no material or inventory link"
                        )

                    db.add(reservation)
                    instance.material_reserved = True
                    instance.updated_at = datetime.utcnow()
                    db.flush()
                    reservations.append(reservation)

        db.commit()
        return [_serialize_reservation(reservation) for reservation in reservations]
    except ValueError as exc:
        db.rollback()
        _handle_value_error(exc)


@router.post(
    "/instances/{instance_id}/issue-material",
    response_model=MaterialReservationOut,
    status_code=status.HTTP_200_OK,
)
async def issue_material(
    instance_id: int,
    data: IssueMaterialRequest,
    current_user: User = Depends(boss_or_supervisor),
    db: Session = Depends(get_db),
):
    if data.component_instance_id != instance_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Instance ID mismatch")

    _get_instance_or_404(db, instance_id)
    reservation = (
        db.query(MaterialReservation)
        .filter(
            MaterialReservation.component_instance_id == instance_id,
            MaterialReservation.status == ReservationStatus.RESERVED,
        )
        .order_by(MaterialReservation.reserved_at.desc())
        .first()
    )
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material reservation not found")

    if data.stock_lot_id is not None:
        lot = db.query(StockLot).filter(StockLot.id == data.stock_lot_id).first()
        if not lot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock lot not found")
        reservation.stock_lot_id = data.stock_lot_id

    reservation.status = ReservationStatus.ISSUED
    reservation.issued_weight_kg = reservation.reserved_weight_kg
    reservation.issued_at = datetime.utcnow()
    reservation.remarks = "Material issued to component instance"

    instance = db.query(ComponentInstance).filter(ComponentInstance.id == instance_id).first()
    instance.material_issued = True
    instance.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(reservation)
    return _serialize_reservation(reservation)


@router.post(
    "/instances/{instance_id}/return-material",
    response_model=MaterialReservationOut,
    status_code=status.HTTP_200_OK,
)
async def return_material(
    instance_id: int,
    data: ReturnMaterialRequest,
    current_user: User = Depends(boss_or_supervisor),
    db: Session = Depends(get_db),
):
    if data.component_instance_id != instance_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Instance ID mismatch")

    instance = _get_instance_or_404(db, instance_id)
    reservation = (
        db.query(MaterialReservation)
        .filter(
            MaterialReservation.component_instance_id == instance_id,
            MaterialReservation.status.in_([ReservationStatus.RESERVED, ReservationStatus.ISSUED]),
        )
        .order_by(MaterialReservation.reserved_at.desc())
        .first()
    )
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material reservation not found")

    try:
        return_weight = Decimal(str(data.weight_kg))
        if return_weight <= 0:
            raise ValueError("Return weight must be greater than zero")

        if reservation.stock_lot_id:
            lot = db.query(StockLot).filter(StockLot.id == reservation.stock_lot_id).with_for_update().first()
            if not lot:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock lot not found")

            weight_before = lot.current_weight_kg
            lot.current_weight_kg = weight_before + return_weight
            lot.is_active = True
            lot.updated_at = datetime.utcnow()

            movement = StockMovement(
                movement_number=get_next_sequence(db, "movement", "MOV"),
                stock_lot_id=lot.id,
                movement_type=MovementType.INWARD_RETURN,
                weight_change_kg=return_weight,
                weight_before_kg=weight_before,
                weight_after_kg=lot.current_weight_kg,
                reference_type="component_instance",
                reference_id=instance.id,
                reason=data.reason or f"Returned from component instance {instance.id}",
                created_by=current_user.id,
                movement_date=datetime.utcnow(),
            )
            db.add(movement)
        elif reservation.inventory_id:
            inventory = db.query(Inventory).filter(Inventory.id == reservation.inventory_id).first()
            if not inventory:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
            inventory.used = max(0.0, round(float(inventory.used) - float(return_weight), 3))

        reservation.status = ReservationStatus.RETURNED
        instance.material_issued = False
        instance.material_reserved = False
        instance.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(reservation)
        return _serialize_reservation(reservation)
    except ValueError as exc:
        db.rollback()
        _handle_value_error(exc)

