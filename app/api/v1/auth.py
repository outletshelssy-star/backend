from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select

from app.core.security.dependencies import get_current_user
from app.core.security.jwt import create_access_token
from app.core.security.password import verify_password
from app.core.security.refresh_token import (
    generate_refresh_token,
    hash_refresh_token,
    verify_refresh_token,
)
from app.db.session import get_session
from app.models.user import User

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
) -> TokenResponse:
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

    refresh_token = generate_refresh_token()
    user.refresh_token_hash = hash_refresh_token(refresh_token)

    session.add(user)
    session.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    data: RefreshRequest,
    session: Session = Depends(get_session),
):
    users = session.exec(
        select(User).where(User.refresh_token_hash != None)  # noqa: E711
    ).all()

    user = next(
        (
            u
            for u in users
            if u.refresh_token_hash is not None
            and verify_refresh_token(data.refresh_token, u.refresh_token_hash)
        ),
        None,
    )

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


@router.post("/logout", status_code=204)
def logout(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    current_user.refresh_token_hash = None
    current_user.token_version += 1
    session.add(current_user)
    session.commit()
