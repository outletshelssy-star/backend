from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import SQLModel

from app.core.security.authorization import require_role
from app.models.enums import UserType
from app.utils.hydrometer import api_60f_crude


class Api60fRequest(SQLModel):
    temp_obs_f: float
    lectura_api: float


class Api60fResponse(SQLModel):
    api_60f: float
    message: str


router = APIRouter(prefix="/hydrometer", tags=["Hydrometer"])


@router.post(
    "/api60f",
    response_model=Api60fResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Valor de temperatura o API fuera de rango"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def calculate_api_60f(
    payload: Api60fRequest,
    _: object = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
) -> Api60fResponse:
    """Calcula el API corregido a 60F a partir de temperatura observada."""
    try:
        api_60f = api_60f_crude(payload.temp_obs_f, payload.lectura_api)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return Api60fResponse(api_60f=api_60f, message="OK")
