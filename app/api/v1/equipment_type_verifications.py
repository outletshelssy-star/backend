from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.enums import UserType
from app.models.equipment_type import EquipmentType
from app.models.equipment_type_verification import (
    EquipmentTypeVerification,
    EquipmentTypeVerificationCreate,
    EquipmentTypeVerificationListResponse,
    EquipmentTypeVerificationRead,
    EquipmentTypeVerificationUpdate,
)
from app.models.equipment_verification import EquipmentVerification
from app.models.user import User

router = APIRouter(
    prefix="/equipment-type-verifications",
    tags=["Equipment Type Verifications"],
)


@router.post(
    "/equipment-type/{equipment_type_id}",
    response_model=EquipmentTypeVerificationRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def create_verification_type(
    equipment_type_id: int,
    payload: EquipmentTypeVerificationCreate,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentTypeVerificationRead:
    """
    Crea un tipo de verificación para un tipo de equipo.

    Permisos: `admin` o `superadmin`.
    Respuestas:
    - 404: recurso no encontrado.
    - 403: permisos insuficientes.
    """
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
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def list_verification_types(
    equipment_type_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
) -> EquipmentTypeVerificationListResponse:
    """
    Lista los tipos de verificación de un tipo de equipo.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    """
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
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def update_verification_type(
    equipment_type_id: int,
    verification_type_id: int,
    payload: EquipmentTypeVerificationUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentTypeVerificationRead:
    """
    Actualiza un tipo de verificación por ID.

    Permisos: `admin` o `superadmin`.
    Respuestas:
    - 404: recurso no encontrado.
    - 403: permisos insuficientes.
    """
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )
    verification_type = session.get(EquipmentTypeVerification, verification_type_id)
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
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
        status.HTTP_409_CONFLICT: {"description": "Existen registros que referencian este tipo"},
    },
)
def delete_verification_type(
    equipment_type_id: int,
    verification_type_id: int,
    reassign_to_id: int | None = Query(
        default=None,
        description="ID del tipo de verificación al que reasignar los registros existentes antes de borrar.",
    ),
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentTypeVerificationRead:
    """
    Elimina un tipo de verificación por ID.

    Si existen verificaciones de equipo que lo referencian, usa `reassign_to_id`
    para moverlas a otro tipo antes de borrar. Sin ese parámetro, retorna 409.

    Permisos: `admin` o `superadmin`.
    """
    equipment_type = session.get(EquipmentType, equipment_type_id)
    if not equipment_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment type not found",
        )
    verification_type = session.get(EquipmentTypeVerification, verification_type_id)
    if (
        not verification_type
        or verification_type.equipment_type_id != equipment_type_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification type not found",
        )

    child_records = session.exec(
        select(EquipmentVerification).where(
            EquipmentVerification.verification_type_id == verification_type_id
        )
    ).all()

    if child_records:
        if reassign_to_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Existen {len(child_records)} verificaciones que referencian este tipo. "
                    "Usa el parámetro reassign_to_id para moverlas a otro tipo antes de borrar."
                ),
            )
        target = session.get(EquipmentTypeVerification, reassign_to_id)
        if not target or target.equipment_type_id != equipment_type_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="reassign_to_id no corresponde a un tipo de verificación válido para este equipo.",
            )
        for record in child_records:
            record.verification_type_id = reassign_to_id
            session.add(record)
        session.flush()

    verification_type_data = EquipmentTypeVerificationRead(
        **verification_type.model_dump()
    )
    session.delete(verification_type)
    session.commit()
    return verification_type_data
