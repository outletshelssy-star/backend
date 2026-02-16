from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.security.authorization import require_role
from app.core.security.dependencies import get_current_active_user
from app.core.security.password import hash_password, verify_password
from app.db.session import get_session
from app.models.company import Company
from app.models.company_block import CompanyBlock
from app.models.company_terminal import CompanyTerminal
from app.models.enums import UserType
from app.models.equipment import Equipment
from app.models.equipment_inspection import EquipmentInspection
from app.models.equipment_reading import EquipmentReading
from app.models.equipment_type import EquipmentType
from app.models.equipment_type_history import EquipmentTypeHistory
from app.models.equipment_type_role_history import EquipmentTypeRoleHistory
from app.models.refs import CompanyRef, CompanyTerminalRef
from app.models.user import (
    User,
    UserCreate,
    UserDeleteResponse,
    UserListResponse,
    UserPasswordUpdate,
    UserReadWithCompany,
    UserUpdateAdmin,
    UserUpdateMe,
)
from app.models.user_terminal import UserTerminal
from app.services.supabase_storage import delete_user_photo, upload_user_photo

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


def _to_user_read_with_company(
    user: User,
    session: Session,
) -> UserReadWithCompany:
    company_ref = None
    if user.company_id is not None:
        company = session.get(Company, user.company_id)
        if company:
            company_ref = CompanyRef(
                **company.model_dump(include={"id", "name", "company_type", "is_active"})
            )
    terminal_refs: list[CompanyTerminalRef] = []
    terminal_ids: list[int] = []
    if _user_type_value(user.user_type) == UserType.superadmin.value:
        all_terminals = session.exec(select(CompanyTerminal)).all()
        for terminal in all_terminals:
            terminal_ids.append(terminal.id)
            terminal_refs.append(
                CompanyTerminalRef(
                    **terminal.model_dump(include={"id", "name", "is_active"})
                )
            )
    else:
        terminal_links = session.exec(
            select(UserTerminal).where(UserTerminal.user_id == user.id)
        ).all()
        for link in terminal_links:
            terminal = session.get(CompanyTerminal, link.terminal_id)
            if terminal:
                terminal_ids.append(terminal.id)
                terminal_refs.append(
                    CompanyTerminalRef(
                        **terminal.model_dump(include={"id", "name", "is_active"})
                    )
                )
    return UserReadWithCompany(
        **user.model_dump(),
        company=company_ref,
        terminals=terminal_refs,
        terminal_ids=terminal_ids,
    )


def _load_terminals(
    session: Session,
    terminal_ids: list[int],
) -> list[CompanyTerminal]:
    if not terminal_ids:
        return []
    terminals = session.exec(
        select(CompanyTerminal).where(CompanyTerminal.id.in_(terminal_ids))
    ).all()
    if len(terminals) != len(set(terminal_ids)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more terminals were not found",
        )
    return terminals


def _user_has_activity(session: Session, user_id: int) -> bool:
    checks = [
        (Company, Company.created_by_user_id),
        (CompanyBlock, CompanyBlock.created_by_user_id),
        (CompanyTerminal, CompanyTerminal.created_by_user_id),
        (EquipmentType, EquipmentType.created_by_user_id),
        (Equipment, Equipment.created_by_user_id),
        (EquipmentInspection, EquipmentInspection.created_by_user_id),
        (EquipmentReading, EquipmentReading.created_by_user_id),
        (EquipmentTypeHistory, EquipmentTypeHistory.changed_by_user_id),
        (EquipmentTypeRoleHistory, EquipmentTypeRoleHistory.changed_by_user_id),
    ]
    for model, field in checks:
        exists = session.exec(select(model).where(field == user_id)).first()
        if exists:
            return True
    return False


def _user_type_value(user_type: UserType | str) -> str:
    if isinstance(user_type, UserType):
        return user_type.value
    return str(user_type)


@router.post(
    "/",
    response_model=UserReadWithCompany,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    user: UserCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> UserReadWithCompany:
    company = session.get(Company, user.company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    db_user = User(
        name=user.name,
        last_name=user.last_name,
        email=user.email,
        user_type=user.user_type,
        photo_url=user.photo_url,
        is_active=user.is_active,
        password_hash=hash_password(user.password),
        company_id=user.company_id,
    )

    session.add(db_user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        ) from None

    session.refresh(db_user)
    if _user_type_value(user.user_type) != UserType.superadmin.value:
        terminals = _load_terminals(session, user.terminal_ids)
        for terminal in terminals:
            session.add(
                UserTerminal(user_id=db_user.id, terminal_id=terminal.id)
            )
        session.commit()
    return _to_user_read_with_company(db_user, session)


@router.get(
    "/",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
)
def list_users(
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
    include: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
) -> Any:
    statement = select(User)
    if is_active is not None:
        statement = statement.where(User.is_active == is_active)
    users = session.exec(statement).all()
    if not users:
        return UserListResponse(message="No records found")
    include_set = {
        item.strip()
        for item in (include or "").split(",")
        if item.strip()
    }
    items = []
    for u in users:
        if include_set:
            items.append(_to_user_read_with_company(u, session))
        else:
            items.append(UserReadWithCompany(**u.model_dump()))
    return UserListResponse(items=items)


@router.get(
    "/me",
    response_model=UserReadWithCompany,
)
def read_me(
    current_user: User = Depends(get_current_active_user),
    include: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    if include:
        return _to_user_read_with_company(current_user, session)
    return UserReadWithCompany(**current_user.model_dump())


@router.put(
    "/me",
    response_model=UserReadWithCompany,
    status_code=status.HTTP_200_OK,
)
def update_me(
    user_in: UserUpdateMe,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> UserReadWithCompany:
    update_data = user_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    return UserReadWithCompany(**current_user.model_dump())


@router.put(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
)
def update_my_password(
    data: UserPasswordUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> None:
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if verify_password(data.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    current_user.password_hash = hash_password(data.new_password)
    session.add(current_user)
    session.commit()


@router.get(
    "/{user_id}",
    response_model=UserReadWithCompany,
)
def get_user(
    user_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
    include: str | None = Query(default=None),
):
    user = session.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if include:
        return _to_user_read_with_company(user, session)

    return UserReadWithCompany(**user.model_dump())


@router.put(
    "/{user_id}",
    response_model=UserReadWithCompany,
)
def update_user(
    user_id: int,
    user_in: UserUpdateAdmin,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> UserReadWithCompany:
    user = session.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == _.id and user_in.is_active is False:
        raise HTTPException(
            status_code=400,
            detail="You cannot deactivate yourself",
        )

    update_data = user_in.model_dump(exclude_unset=True)

    if "company_id" in update_data:
        company_id = update_data["company_id"]
        if company_id is not None:
            company = session.get(Company, company_id)
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Company not found",
                )
    terminal_ids = update_data.pop("terminal_ids", None)

    for field, value in update_data.items():
        setattr(user, field, value)

    session.add(user)
    session.commit()
    session.refresh(user)

    if terminal_ids is not None:
        existing_links = session.exec(
            select(UserTerminal).where(UserTerminal.user_id == user.id)
        ).all()
        for link in existing_links:
            session.delete(link)
        if _user_type_value(user.user_type) != UserType.superadmin.value:
            terminals = _load_terminals(session, terminal_ids)
            for terminal in terminals:
                session.add(
                    UserTerminal(user_id=user.id, terminal_id=terminal.id)
                )
        session.commit()

    return _to_user_read_with_company(user, session)


@router.post(
    "/me/photo",
    response_model=UserReadWithCompany,
    status_code=status.HTTP_200_OK,
)
def upload_my_photo(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
) -> UserReadWithCompany:
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no ID",
        )

    photo_url = upload_user_photo(file, current_user.id)
    current_user.photo_url = photo_url

    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    return UserReadWithCompany(**current_user.model_dump())


@router.post(
    "/{user_id}/photo",
    response_model=UserReadWithCompany,
    status_code=status.HTTP_200_OK,
)
def upload_photo(
    user_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> UserReadWithCompany:
    user = session.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    photo_url = upload_user_photo(file, user_id)
    user.photo_url = photo_url

    session.add(user)
    session.commit()
    session.refresh(user)

    return UserReadWithCompany(**user.model_dump())


@router.delete(
    "/{user_id}",
    response_model=UserDeleteResponse,
    status_code=status.HTTP_200_OK,
)
def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> UserDeleteResponse:
    user = session.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete yourself",
        )
    if (
        _user_type_value(current_user.user_type) == UserType.admin.value
        and _user_type_value(user.user_type) == UserType.superadmin.value
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users cannot delete superadmin accounts",
        )

    if _user_has_activity(session, user_id):
        user.is_active = False
        session.add(user)
        session.commit()
        session.refresh(user)
        return UserDeleteResponse(
            action="deactivated",
            message="User has related records. User deactivated.",
            user=_to_user_read_with_company(user, session),
        )

    if user.photo_url:
        delete_user_photo(user.photo_url)

    session.delete(user)
    session.commit()
    return UserDeleteResponse(
        action="deleted",
        message="User deleted successfully.",
        user=None,
    )
