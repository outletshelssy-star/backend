from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.security.dependencies import get_current_user
from app.core.security.jwt import create_access_token
from app.core.security.password import hash_password, needs_rehash, verify_password
from app.core.security.refresh_token import (
    generate_refresh_token,
    hash_refresh_token,
)
from app.db.session import get_session
from app.models.user import User

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Credenciales inválidas o token expirado"},
        status.HTTP_403_FORBIDDEN: {"description": "Usuario inactivo"},
    },
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
) -> TokenResponse:
    """
    Inicia sesión y retorna tokens de acceso y refresco.

    Permisos: público (sin autenticación previa).
    Respuestas:
    - 401: credenciales inválidas.
    - 403: usuario inactivo.
    """
    statement = select(User).where(User.email == form_data.username)
    user = session.exec(statement).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    if user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no ID",
        )

    access_token = create_access_token(
        subject=user.id,
        token_version=user.token_version,
    )

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(form_data.password)

    refresh_token = generate_refresh_token()
    user.refresh_token_hash = hash_refresh_token(refresh_token)

    session.add(user)
    session.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Refresh token inválido"},
    },
)
def refresh_token(
    data: RefreshRequest,
    session: Session = Depends(get_session),
) -> TokenResponse:
    """
    Renueva el access token usando un refresh token válido.

    Permisos: público (con refresh token).
    Respuestas:
    - 401: refresh token inválido.
    """
    token_hash = hash_refresh_token(data.refresh_token)
    user = session.exec(
        select(User).where(User.refresh_token_hash == token_hash)
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no ID",
        )

    new_access_token = create_access_token(
        subject=user.id,
        token_version=user.token_version,
    )
    new_refresh_token = generate_refresh_token()

    user.refresh_token_hash = hash_refresh_token(new_refresh_token)

    session.add(user)
    session.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


@router.post(
    "/logout",
    status_code=204,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Token inválido o expirado"},
    },
)
def logout(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    """
    Cierra sesión invalidando el refresh token actual.

    Permisos: autenticado.
    Respuestas:
    - 401: token inválido o expirado.
    """
    current_user.refresh_token_hash = None
    current_user.token_version += 1
    session.add(current_user)
    session.commit()
