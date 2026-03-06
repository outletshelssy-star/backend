import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Field, SQLModel

from app.core.bootstrap import bootstrap_database, should_seed_development_data
from app.core.config import get_settings
from app.core.security.authorization import require_role
from app.models.enums import UserType
from app.models.user import User

logger = logging.getLogger("uvicorn.error")


class BootstrapRunRequest(SQLModel):
    include_development_data: bool = Field(
        default=False,
        description=(
            "Si es true y el ambiente es development, repone tambien "
            "los catalogos y datos base de desarrollo."
        ),
    )


class BootstrapRunResponse(SQLModel):
    message: str
    app_env: str
    include_development_data: bool


router = APIRouter(
    prefix="/bootstrap",
    tags=["Bootstrap"],
)


@router.post(
    "/",
    response_model=BootstrapRunResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Bootstrap no disponible"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Fallo interno"},
    },
)
def run_bootstrap(
    payload: BootstrapRunRequest,
    _: User = Depends(require_role(UserType.superadmin)),
) -> BootstrapRunResponse:
    """
    Ejecuta el bootstrap manualmente.

    Permisos: `superadmin`.
    """
    settings = get_settings()
    if settings.app_env == "test":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bootstrap is disabled in test environment",
        )

    resolved_include_development_data = should_seed_development_data(
        app_env=settings.app_env,
        include_development_data=payload.include_development_data,
    )

    try:
        bootstrap_database(
            app_env=settings.app_env,
            include_development_data=payload.include_development_data,
        )
    except Exception as err:
        logger.exception("Failed to run bootstrap manually")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bootstrap failed",
        ) from err

    return BootstrapRunResponse(
        message="Bootstrap completed successfully",
        app_env=settings.app_env,
        include_development_data=resolved_include_development_data,
    )
