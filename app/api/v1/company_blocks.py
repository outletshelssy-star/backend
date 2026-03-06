from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.company import Company
from app.models.company_block import (
    CompanyBlock,
    CompanyBlockCreate,
    CompanyBlockDeleteResponse,
    CompanyBlockListResponse,
    CompanyBlockReadWithIncludes,
    CompanyBlockUpdate,
)
from app.models.company_terminal import CompanyTerminal
from app.models.enums import UserType
from app.models.refs import CompanyRef, CompanyTerminalRef, UserRef
from app.models.user import User

router = APIRouter(
    prefix="/company-blocks",
    tags=["Company Blocks"],
)


def _to_company_ref(company: Company) -> CompanyRef:
    if company.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Company has no ID",
        )
    return CompanyRef(
        id=company.id,
        name=company.name,
        company_type=company.company_type,
        is_active=company.is_active,
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


def _parse_include_set(include: str | None) -> set[str]:
    return {item.strip() for item in (include or "").split(",") if item.strip()}


def _build_company_block_read_with_includes(
    block: CompanyBlock,
    *,
    include_set: set[str],
    companies_by_id: dict[int, Company] | None = None,
    users_by_id: dict[int, User] | None = None,
    terminals_by_block_id: dict[int, list[CompanyTerminalRef]] | None = None,
) -> CompanyBlockReadWithIncludes:
    block_company: CompanyRef | None = None
    if "company" in include_set and companies_by_id is not None:
        block_company_db = companies_by_id.get(block.company_id)
        if block_company_db is not None:
            block_company = _to_company_ref(block_company_db)

    creator: UserRef | None = None
    if "creator" in include_set and users_by_id is not None:
        creator_db = users_by_id.get(block.created_by_user_id)
        if creator_db is not None:
            creator = _to_user_ref(creator_db)

    terminals: list[CompanyTerminalRef] = []
    if (
        "terminals" in include_set
        and terminals_by_block_id is not None
        and block.id is not None
    ):
        terminals = terminals_by_block_id.get(block.id, [])

    return CompanyBlockReadWithIncludes(
        **block.model_dump(),
        company=block_company,
        creator=creator,
        terminals=terminals,
    )


@router.post(
    "/",
    response_model=CompanyBlockReadWithIncludes,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def create_company_block(
    block_in: CompanyBlockCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> CompanyBlockReadWithIncludes:
    """
    Crea un bloque para una empresa.

    Permisos: `admin` o `superadmin`.
    """
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no ID",
        )

    company = session.get(Company, block_in.company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    block = CompanyBlock(
        name=block_in.name,
        is_active=block_in.is_active,
        company_id=block_in.company_id,
        created_by_user_id=current_user.id,
    )

    session.add(block)
    session.commit()
    session.refresh(block)
    return CompanyBlockReadWithIncludes(**block.model_dump())


@router.get(
    "/",
    response_model=CompanyBlockListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def list_company_blocks(
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
    include: str | None = Query(
        default=None,
        description=(
            "Relaciones a incluir, separadas por coma: "
            "`company`, `creator`, `terminals`."
        ),
    ),
    company_id: int | None = Query(
        default=None,
        description="Filtrar por ID de empresa.",
    ),
) -> CompanyBlockListResponse:
    """
    Lista bloques de empresa con filtros y relaciones opcionales.

    Permisos: `admin` o `superadmin`.
    """
    statement = select(CompanyBlock)
    if company_id is not None:
        statement = statement.where(CompanyBlock.company_id == company_id)
    blocks = session.exec(statement).all()
    if not blocks:
        return CompanyBlockListResponse(message="No records found")
    include_set = _parse_include_set(include)
    if not include_set:
        return CompanyBlockListResponse(
            items=[CompanyBlockReadWithIncludes(**b.model_dump()) for b in blocks]
        )

    companies_by_id: dict[int, Company] = {}
    if "company" in include_set:
        company_ids = {block.company_id for block in blocks}
        companies_by_id = {
            company.id: company
            for company in session.exec(
                select(Company).where(Company.id.in_(company_ids))  # type: ignore[attr-defined]
            ).all()
            if company.id is not None
        }

    users_by_id: dict[int, User] = {}
    if "creator" in include_set:
        user_ids = {block.created_by_user_id for block in blocks}
        users_by_id = {
            user.id: user
            for user in session.exec(
                select(User).where(User.id.in_(user_ids))  # type: ignore[attr-defined]
            ).all()
            if user.id is not None
        }

    terminals_by_block_id: dict[int, list[CompanyTerminalRef]] = {}
    if "terminals" in include_set:
        block_ids = [block.id for block in blocks if block.id is not None]
        if block_ids:
            terminals = session.exec(
                select(CompanyTerminal).where(
                    CompanyTerminal.block_id.in_(block_ids)  # type: ignore[attr-defined]
                )
            ).all()
            for terminal in terminals:
                if terminal.id is None:
                    continue
                terminals_by_block_id.setdefault(terminal.block_id, []).append(
                    _to_company_terminal_ref(terminal)
                )

    results = [
        _build_company_block_read_with_includes(
            block,
            include_set=include_set,
            companies_by_id=companies_by_id,
            users_by_id=users_by_id,
            terminals_by_block_id=terminals_by_block_id,
        )
        for block in blocks
    ]
    return CompanyBlockListResponse(items=results)


@router.get(
    "/{block_id}",
    response_model=CompanyBlockReadWithIncludes,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def get_company_block(
    block_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
    include: str | None = Query(
        default=None,
        description=(
            "Relaciones a incluir, separadas por coma: "
            "`company`, `creator`, `terminals`."
        ),
    ),
    company_id: int = Query(
        ...,
        description=(
            "ID de la empresa propietaria del bloque. "
            "Se valida que el bloque pertenezca a esta empresa."
        ),
    ),
) -> CompanyBlockReadWithIncludes:
    """
    Obtiene un bloque por ID, validando que pertenece a la empresa indicada.

    Permisos: `admin` o `superadmin`.
    """
    block = session.get(CompanyBlock, block_id)
    if not block or block.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company block not found",
        )
    include_set = _parse_include_set(include)
    if not include_set:
        return CompanyBlockReadWithIncludes(**block.model_dump())

    companies_by_id: dict[int, Company] = {}
    if "company" in include_set:
        block_company_db = session.get(Company, block.company_id)
        if block_company_db is not None:
            companies_by_id[block.company_id] = block_company_db

    users_by_id: dict[int, User] = {}
    if "creator" in include_set:
        creator_db = session.get(User, block.created_by_user_id)
        if creator_db is not None:
            users_by_id[block.created_by_user_id] = creator_db

    terminals_by_block_id: dict[int, list[CompanyTerminalRef]] = {}
    if "terminals" in include_set and block.id is not None:
        terminals_by_block_id[block.id] = [
            _to_company_terminal_ref(terminal)
            for terminal in session.exec(
                select(CompanyTerminal).where(CompanyTerminal.block_id == block.id)
            ).all()
            if terminal.id is not None
        ]

    return _build_company_block_read_with_includes(
        block,
        include_set=include_set,
        companies_by_id=companies_by_id,
        users_by_id=users_by_id,
        terminals_by_block_id=terminals_by_block_id,
    )


@router.put(
    "/{block_id}",
    response_model=CompanyBlockReadWithIncludes,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def update_company_block(
    block_id: int,
    block_in: CompanyBlockUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> CompanyBlockReadWithIncludes:
    """
    Actualiza un bloque por ID.

    Permisos: `admin` o `superadmin`.
    """
    block = session.get(CompanyBlock, block_id)
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company block not found",
        )

    update_data = block_in.model_dump(exclude_unset=True)
    if "company_id" in update_data:
        company = session.get(Company, update_data["company_id"])
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found",
            )

    for field, value in update_data.items():
        setattr(block, field, value)

    session.add(block)
    session.commit()
    session.refresh(block)
    return CompanyBlockReadWithIncludes(**block.model_dump())


@router.delete(
    "/{block_id}",
    response_model=CompanyBlockDeleteResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def delete_company_block(
    block_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> CompanyBlockDeleteResponse:
    """
    Elimina un bloque por ID.

    Permisos: `admin` o `superadmin`.
    """
    block = session.get(CompanyBlock, block_id)
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company block not found",
        )

    block_data = CompanyBlockReadWithIncludes(**block.model_dump())
    session.delete(block)
    session.commit()
    return CompanyBlockDeleteResponse(
        action="deleted",
        message="Company block deleted successfully.",
        block=block_data,
    )
