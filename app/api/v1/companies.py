from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.company import (
    Company,
    CompanyCreate,
    CompanyDeleteResponse,
    CompanyListResponse,
    CompanyReadWithIncludes,
    CompanyUpdate,
)
from app.models.company_block import CompanyBlock
from app.models.company_terminal import CompanyTerminal
from app.models.enums import UserType
from app.models.refs import CompanyBlockRef, CompanyTerminalRef, UserRef
from app.models.user import User

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)


def _to_user_ref(user: User) -> UserRef:
    if user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no ID",
        )
    return UserRef(
        id=user.id,
        name=user.name,
        last_name=user.last_name,
        email=user.email,
        user_type=user.user_type,
    )


def _to_company_block_ref(block: CompanyBlock) -> CompanyBlockRef:
    if block.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Company block has no ID",
        )
    return CompanyBlockRef(
        id=block.id,
        name=block.name,
        is_active=block.is_active,
    )


def _to_company_terminal_ref(terminal: CompanyTerminal) -> CompanyTerminalRef:
    if terminal.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Company terminal has no ID",
        )
    return CompanyTerminalRef(
        id=terminal.id,
        name=terminal.name,
        is_active=terminal.is_active,
    )


@router.post(
    "/",
    response_model=CompanyReadWithIncludes,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def create_company(
    company_in: CompanyCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> CompanyReadWithIncludes:
    """
    Crea una empresa.

    Permisos: `admin` o `superadmin`.
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no ID",
        )

    company = Company(
        name=company_in.name,
        company_type=company_in.company_type,
        is_active=company_in.is_active,
        created_by_user_id=current_user.id,
    )

    session.add(company)
    session.commit()
    session.refresh(company)
    return CompanyReadWithIncludes(**company.model_dump())


@router.get(
    "/",
    response_model=CompanyListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def list_companies(
    session: Session = Depends(get_session),
    _: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
    include: str | None = Query(
        default=None,
        description="Relaciones a incluir, separadas por coma: `creator`, `blocks`, `terminals`.",
    ),
) -> CompanyListResponse:
    """
    Lista empresas y opcionalmente incluye relaciones.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Parámetros:
    - `include`: lista separada por comas (`creator`, `blocks`, `terminals`).
    """
    statement = select(Company)
    companies = session.exec(statement).all()
    if not companies:
        return CompanyListResponse(message="No records found")

    include_set = {item.strip() for item in (include or "").split(",") if item.strip()}

    if not include_set:
        return CompanyListResponse(
            items=[CompanyReadWithIncludes(**c.model_dump()) for c in companies]
        )

    results: list[CompanyReadWithIncludes] = []
    for company in companies:
        creator: UserRef | None = None
        if "creator" in include_set:
            creator_db = session.get(User, company.created_by_user_id)
            if creator_db is not None:
                creator = _to_user_ref(creator_db)
        blocks: list[CompanyBlockRef] = []
        if "blocks" in include_set and company.id is not None:
            blocks = [
                _to_company_block_ref(block)
                for block in session.exec(
                    select(CompanyBlock).where(CompanyBlock.company_id == company.id)
                ).all()
                if block.id is not None
            ]
        terminals: list[CompanyTerminalRef] = []
        if "terminals" in include_set and company.id is not None:
            terminals = [
                _to_company_terminal_ref(terminal)
                for terminal in session.exec(
                    select(CompanyTerminal).where(
                        CompanyTerminal.owner_company_id == company.id
                    )
                ).all()
                if terminal.id is not None
            ]
        results.append(
            CompanyReadWithIncludes(
                **company.model_dump(),
                creator=creator,
                blocks=blocks,
                terminals=terminals,
            )
        )
    return CompanyListResponse(items=results)


@router.get(
    "/{company_id}",
    response_model=CompanyReadWithIncludes,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Empresa no encontrada"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def get_company(
    company_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
    include: str | None = Query(
        default=None,
        description="Relaciones a incluir, separadas por coma: `creator`, `blocks`, `terminals`.",
    ),
) -> CompanyReadWithIncludes:
    """
    Obtiene una empresa por ID y opcionalmente incluye relaciones.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Parámetros:
    - `company_id`: ID de la empresa.
    - `include`: lista separada por comas (`creator`, `blocks`, `terminals`).
    """
    company = session.get(Company, company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    include_set = {item.strip() for item in (include or "").split(",") if item.strip()}
    if not include_set:
        return CompanyReadWithIncludes(**company.model_dump())

    creator: UserRef | None = None
    if "creator" in include_set:
        creator_db = session.get(User, company.created_by_user_id)
        if creator_db is not None:
            creator = _to_user_ref(creator_db)
    blocks: list[CompanyBlockRef] = []
    if "blocks" in include_set and company.id is not None:
        blocks = [
            _to_company_block_ref(block)
            for block in session.exec(
                select(CompanyBlock).where(CompanyBlock.company_id == company.id)
            ).all()
            if block.id is not None
        ]
    terminals: list[CompanyTerminalRef] = []
    if "terminals" in include_set and company.id is not None:
        terminals = [
            _to_company_terminal_ref(terminal)
            for terminal in session.exec(
                select(CompanyTerminal).where(
                    CompanyTerminal.owner_company_id == company.id
                )
            ).all()
            if terminal.id is not None
        ]

    return CompanyReadWithIncludes(
        **company.model_dump(),
        creator=creator,
        blocks=blocks,
        terminals=terminals,
    )


@router.put(
    "/{company_id}",
    response_model=CompanyReadWithIncludes,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Empresa no encontrada"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def update_company(
    company_id: int,
    company_in: CompanyUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> CompanyReadWithIncludes:
    """
    Actualiza una empresa por ID.

    Permisos: `admin` o `superadmin`.
    """
    company = session.get(Company, company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    update_data = company_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)

    session.add(company)
    session.commit()
    session.refresh(company)

    return CompanyReadWithIncludes(**company.model_dump())


@router.delete(
    "/{company_id}",
    response_model=CompanyDeleteResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Empresa no encontrada"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def delete_company(
    company_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> CompanyDeleteResponse:
    """
    Elimina una empresa por ID.

    Permisos: `admin` o `superadmin`.
    """
    company = session.get(Company, company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    company_data = CompanyReadWithIncludes(**company.model_dump())
    session.delete(company)
    session.commit()
    return CompanyDeleteResponse(
        action="deleted",
        message="Company deleted successfully.",
        company=company_data,
    )
