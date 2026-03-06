from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.enums import UserType
from app.models.equipment import Equipment
from app.models.equipment_verification import (
    EquipmentVerification,
    EquipmentVerificationListResponse,
    EquipmentVerificationRead,
    EquipmentVerificationResponse,
    EquipmentVerificationResponseRead,
)
from app.models.user import User
from app.models.user_terminal import UserTerminal

router = APIRouter()
@router.get(
    "/equipment/{equipment_id}",
    response_model=EquipmentVerificationListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def list_equipment_verifications(
    equipment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> EquipmentVerificationListResponse:
    """
    Lista verificaciones de un equipo.

    Permisos: `user`, `admin`, `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: equipo no encontrado.
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no ID",
        )

    equipment = session.get(Equipment, equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )

    if current_user.user_type != UserType.superadmin:
        allowed_terminal_ids = session.exec(
            select(UserTerminal.terminal_id).where(
                UserTerminal.user_id == current_user.id
            )
        ).all()
        if allowed_terminal_ids and equipment.terminal_id not in set(
            allowed_terminal_ids
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this terminal",
            )

    verifications = session.exec(
        select(EquipmentVerification).where(
            EquipmentVerification.equipment_id == equipment.id
        )
    ).all()
    if not verifications:
        return EquipmentVerificationListResponse(message="No records found")
    items = []
    for verification in verifications:
        responses = session.exec(
            select(EquipmentVerificationResponse).where(
                EquipmentVerificationResponse.verification_id == verification.id
            )
        ).all()
        items.append(
            EquipmentVerificationRead(
                **verification.model_dump(),
                responses=[
                    EquipmentVerificationResponseRead.model_validate(
                        r, from_attributes=True
                    )
                    for r in responses
                ],
            )
        )
    return EquipmentVerificationListResponse(items=items)


@router.get(
    "/{verification_id}",
    response_model=EquipmentVerificationRead,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def get_verification(
    verification_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> EquipmentVerificationRead:
    """
    Obtiene una verificaciÃ³n por ID.

    Permisos: `admin`, `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: recurso no encontrado.
    """
    verification = session.get(EquipmentVerification, verification_id)
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification not found",
        )
    responses = session.exec(
        select(EquipmentVerificationResponse).where(
            EquipmentVerificationResponse.verification_id == verification.id
        )
    ).all()
    return EquipmentVerificationRead(
        **verification.model_dump(),
        responses=[
            EquipmentVerificationResponseRead.model_validate(r, from_attributes=True)
            for r in responses
        ],
    )

