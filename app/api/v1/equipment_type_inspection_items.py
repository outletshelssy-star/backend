from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.enums import UserType
from app.models.equipment_inspection import EquipmentInspectionResponse
from app.models.equipment_type import EquipmentType
from app.models.equipment_type_inspection_item import (
    EquipmentTypeInspectionItem,
    EquipmentTypeInspectionItemBulkCreate,
    EquipmentTypeInspectionItemCreate,
    EquipmentTypeInspectionItemListResponse,
    EquipmentTypeInspectionItemRead,
    EquipmentTypeInspectionItemUpdate,
)
from app.models.user import User

router = APIRouter(
    prefix="/equipment-type-inspection-items",
    tags=["Equipment Type Inspection Items"],
)


@router.post(
    "/equipment-type/{equipment_type_id}",
    response_model=EquipmentTypeInspectionItemRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def create_inspection_item(
    equipment_type_id: int,
    payload: EquipmentTypeInspectionItemCreate,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentTypeInspectionItemRead:
    """
    Crea un ítem de inspección para un tipo de equipo.

    Permisos: `admin` o `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: tipo de equipo no encontrado.
    """
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )
    item = EquipmentTypeInspectionItem(
        equipment_type_id=equipment_type_id,
        item=payload.item,
        response_type=payload.response_type,
        is_required=payload.is_required,
        order=payload.order,
        expected_bool=payload.expected_bool,
        expected_text_options=payload.expected_text_options,
        expected_number=payload.expected_number,
        expected_number_min=payload.expected_number_min,
        expected_number_max=payload.expected_number_max,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return EquipmentTypeInspectionItemRead(**item.model_dump())


@router.post(
    "/equipment-type/{equipment_type_id}/bulk",
    response_model=EquipmentTypeInspectionItemListResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def create_inspection_items_bulk(
    equipment_type_id: int,
    payload: EquipmentTypeInspectionItemBulkCreate,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentTypeInspectionItemListResponse:
    """
    Crea múltiples ítems de inspección para un tipo de equipo.

    Permisos: `admin` o `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: tipo de equipo no encontrado.
    """
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )
    if not payload.items:
        return EquipmentTypeInspectionItemListResponse(message="No records found")

    items: list[EquipmentTypeInspectionItem] = []
    for item_in in payload.items:
        items.append(
            EquipmentTypeInspectionItem(
                equipment_type_id=equipment_type_id,
                item=item_in.item,
                response_type=item_in.response_type,
                is_required=item_in.is_required,
                order=item_in.order,
                expected_bool=item_in.expected_bool,
                expected_text_options=item_in.expected_text_options,
                expected_number=item_in.expected_number,
                expected_number_min=item_in.expected_number_min,
                expected_number_max=item_in.expected_number_max,
            )
        )
    session.add_all(items)
    session.commit()
    for item in items:
        session.refresh(item)

    return EquipmentTypeInspectionItemListResponse(
        items=[EquipmentTypeInspectionItemRead(**i.model_dump()) for i in items]
    )


@router.get(
    "/equipment-type/{equipment_type_id}",
    response_model=EquipmentTypeInspectionItemListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def list_inspection_items(
    equipment_type_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
) -> Any:
    """
    Lista los ítems de inspección de un tipo de equipo.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: tipo de equipo no encontrado.
    """
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )

    items = session.exec(
        select(EquipmentTypeInspectionItem)
        .where(EquipmentTypeInspectionItem.equipment_type_id == equipment_type_id)
        .order_by(EquipmentTypeInspectionItem.order)  # type: ignore[arg-type]
    ).all()
    if not items:
        return EquipmentTypeInspectionItemListResponse(message="No records found")
    return EquipmentTypeInspectionItemListResponse(
        items=[EquipmentTypeInspectionItemRead(**i.model_dump()) for i in items]
    )


@router.put(
    "/equipment-type/{equipment_type_id}/{item_id}",
    response_model=EquipmentTypeInspectionItemRead,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def update_inspection_item(
    equipment_type_id: int,
    item_id: int,
    payload: EquipmentTypeInspectionItemUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentTypeInspectionItemRead:
    """
    Actualiza un ítem de inspección por ID.

    Permisos: `admin` o `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: tipo de equipo o ítem no encontrado.
    """
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )
    item = session.get(EquipmentTypeInspectionItem, item_id)
    if not item or item.equipment_type_id != equipment_type_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection item not found",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    session.add(item)
    session.commit()
    session.refresh(item)
    return EquipmentTypeInspectionItemRead(**item.model_dump())


@router.delete(
    "/equipment-type/{equipment_type_id}/{item_id}",
    response_model=EquipmentTypeInspectionItemRead,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
        status.HTTP_409_CONFLICT: {"description": "Conflicto: recurso referenciado"},
    },
)
def delete_inspection_item(
    equipment_type_id: int,
    item_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentTypeInspectionItemRead:
    """
    Elimina un ítem de inspección por ID.

    Permisos: `admin` o `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: tipo de equipo o ítem no encontrado.
    - 409: el ítem tiene respuestas registradas y no puede eliminarse.
    """
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )
    item = session.get(EquipmentTypeInspectionItem, item_id)
    if not item or item.equipment_type_id != equipment_type_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection item not found",
        )
    referenced = session.exec(
        select(EquipmentInspectionResponse.id).where(
            EquipmentInspectionResponse.inspection_item_id == item.id
        )
    ).first()
    if referenced:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inspection item has responses and cannot be deleted.",
        )
    item_data = EquipmentTypeInspectionItemRead(**item.model_dump())
    session.delete(item)
    session.commit()
    return item_data
