from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.equipment_type import EquipmentType
from app.models.equipment_type_verification_item import (
    EquipmentTypeVerificationItem,
    EquipmentTypeVerificationItemBulkCreate,
    EquipmentTypeVerificationItemCreate,
    EquipmentTypeVerificationItemListResponse,
    EquipmentTypeVerificationItemRead,
    EquipmentTypeVerificationItemUpdate,
)
from app.models.equipment_type_verification import (
    EquipmentTypeVerification,
)
from app.models.enums import UserType
from app.models.user import User

router = APIRouter(
    prefix="/equipment-type-verification-items",
    tags=["Equipment Type Verification Items"],
)


def _resolve_verification_type_id(
    session: Session,
    equipment_type_id: int,
    verification_type_id: int | None,
) -> int:
    if verification_type_id is not None:
        verification_type = session.get(
            EquipmentTypeVerification, verification_type_id
        )
        if (
            not verification_type
            or verification_type.equipment_type_id != equipment_type_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification_type_id for this equipment type",
            )
        return verification_type_id

    verification_types = session.exec(
        select(EquipmentTypeVerification).where(
            EquipmentTypeVerification.equipment_type_id == equipment_type_id,
            EquipmentTypeVerification.is_active == True,  # noqa: E712
        )
    ).all()
    if len(verification_types) == 1 and verification_types[0].id is not None:
        return verification_types[0].id
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="verification_type_id is required for this equipment type",
    )


@router.post(
    "/equipment-type/{equipment_type_id}",
    response_model=EquipmentTypeVerificationItemRead,
    status_code=status.HTTP_201_CREATED,
)
def create_verification_item(
    equipment_type_id: int,
    payload: EquipmentTypeVerificationItemCreate,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentTypeVerificationItemRead:
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )
    verification_type_id = _resolve_verification_type_id(
        session, equipment_type_id, payload.verification_type_id
    )
    item = EquipmentTypeVerificationItem(
        equipment_type_id=equipment_type_id,
        verification_type_id=verification_type_id,
        **payload.model_dump(exclude={"verification_type_id"}),
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return EquipmentTypeVerificationItemRead(**item.model_dump())


@router.post(
    "/equipment-type/{equipment_type_id}/bulk",
    response_model=EquipmentTypeVerificationItemListResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_verification_items_bulk(
    equipment_type_id: int,
    payload: EquipmentTypeVerificationItemBulkCreate,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentTypeVerificationItemListResponse:
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )
    items = []
    for item in payload.items:
        verification_type_id = _resolve_verification_type_id(
            session, equipment_type_id, item.verification_type_id
        )
        entry = EquipmentTypeVerificationItem(
            equipment_type_id=equipment_type_id,
            verification_type_id=verification_type_id,
            **item.model_dump(exclude={"verification_type_id"}),
        )
        session.add(entry)
        items.append(entry)
    session.commit()
    return EquipmentTypeVerificationItemListResponse(
        items=[EquipmentTypeVerificationItemRead(**item.model_dump()) for item in items]
    )


@router.get(
    "/equipment-type/{equipment_type_id}",
    response_model=EquipmentTypeVerificationItemListResponse,
    status_code=status.HTTP_200_OK,
)
def list_verification_items(
    equipment_type_id: int,
    verification_type_id: int | None = None,
    session: Session = Depends(get_session),
    _: User = Depends(
        require_role(UserType.visitor, UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> Any:
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )
    query = select(EquipmentTypeVerificationItem).where(
        EquipmentTypeVerificationItem.equipment_type_id == equipment_type_id
    )
    if verification_type_id is not None:
        _resolve_verification_type_id(
            session, equipment_type_id, verification_type_id
        )
        query = query.where(
            EquipmentTypeVerificationItem.verification_type_id
            == verification_type_id
        )
    items = session.exec(query).all()
    if not items:
        return EquipmentTypeVerificationItemListResponse(message="No records found")
    return EquipmentTypeVerificationItemListResponse(
        items=[EquipmentTypeVerificationItemRead(**item.model_dump()) for item in items]
    )


@router.put(
    "/equipment-type/{equipment_type_id}/{item_id}",
    response_model=EquipmentTypeVerificationItemRead,
    status_code=status.HTTP_200_OK,
)
def update_verification_item(
    equipment_type_id: int,
    item_id: int,
    payload: EquipmentTypeVerificationItemUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentTypeVerificationItemRead:
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )
    item = session.get(EquipmentTypeVerificationItem, item_id)
    if not item or item.equipment_type_id != equipment_type_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification item not found",
        )
    if payload.verification_type_id is not None:
        _resolve_verification_type_id(
            session, equipment_type_id, payload.verification_type_id
        )
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return EquipmentTypeVerificationItemRead(**item.model_dump())


@router.delete(
    "/equipment-type/{equipment_type_id}/{item_id}",
    response_model=EquipmentTypeVerificationItemRead,
    status_code=status.HTTP_200_OK,
)
def delete_verification_item(
    equipment_type_id: int,
    item_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentTypeVerificationItemRead:
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )
    item = session.get(EquipmentTypeVerificationItem, item_id)
    if not item or item.equipment_type_id != equipment_type_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification item not found",
        )
    item_data = EquipmentTypeVerificationItemRead(**item.model_dump())
    session.delete(item)
    session.commit()
    return item_data
