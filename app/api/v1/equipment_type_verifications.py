from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.equipment_type import EquipmentType
from app.models.equipment_type_verification import (
    EquipmentTypeVerification,
    EquipmentTypeVerificationCreate,
    EquipmentTypeVerificationListResponse,
    EquipmentTypeVerificationRead,
    EquipmentTypeVerificationUpdate,
)
from app.models.enums import UserType
from app.models.user import User

router = APIRouter(
    prefix="/equipment-type-verifications",
    tags=["Equipment Type Verifications"],
)


@router.post(
    "/equipment-type/{equipment_type_id}",
    response_model=EquipmentTypeVerificationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_verification_type(
    equipment_type_id: int,
    payload: EquipmentTypeVerificationCreate,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentTypeVerificationRead:
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )
    verification_type = EquipmentTypeVerification(
        equipment_type_id=equipment_type_id,
        **payload.model_dump(),
    )
    session.add(verification_type)
    session.commit()
    session.refresh(verification_type)
    return EquipmentTypeVerificationRead(**verification_type.model_dump())


@router.get(
    "/equipment-type/{equipment_type_id}",
    response_model=EquipmentTypeVerificationListResponse,
    status_code=status.HTTP_200_OK,
)
def list_verification_types(
    equipment_type_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> EquipmentTypeVerificationListResponse:
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )
    items = session.exec(
        select(EquipmentTypeVerification).where(
            EquipmentTypeVerification.equipment_type_id == equipment_type_id
        )
    ).all()
    if not items:
        return EquipmentTypeVerificationListResponse(message="No records found")
    return EquipmentTypeVerificationListResponse(
        items=[EquipmentTypeVerificationRead(**item.model_dump()) for item in items]
    )


@router.put(
    "/equipment-type/{equipment_type_id}/{verification_type_id}",
    response_model=EquipmentTypeVerificationRead,
    status_code=status.HTTP_200_OK,
)
def update_verification_type(
    equipment_type_id: int,
    verification_type_id: int,
    payload: EquipmentTypeVerificationUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentTypeVerificationRead:
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )
    verification_type = session.get(
        EquipmentTypeVerification, verification_type_id
    )
    if (
        not verification_type
        or verification_type.equipment_type_id != equipment_type_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification type not found",
        )
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(verification_type, field, value)
    session.add(verification_type)
    session.commit()
    session.refresh(verification_type)
    return EquipmentTypeVerificationRead(**verification_type.model_dump())


@router.delete(
    "/equipment-type/{equipment_type_id}/{verification_type_id}",
    response_model=EquipmentTypeVerificationRead,
    status_code=status.HTTP_200_OK,
)
def delete_verification_type(
    equipment_type_id: int,
    verification_type_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentTypeVerificationRead:
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )
    verification_type = session.get(
        EquipmentTypeVerification, verification_type_id
    )
    if (
        not verification_type
        or verification_type.equipment_type_id != equipment_type_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification type not found",
        )
    verification_type_data = EquipmentTypeVerificationRead(
        **verification_type.model_dump()
    )
    session.delete(verification_type)
    session.commit()
    return verification_type_data
