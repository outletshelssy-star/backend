from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Any
from sqlmodel import Session, select

from app.core.security.authorization import require_role
from app.core.security.dependencies import get_current_active_user
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
from app.models.user import User

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)


@router.post(
    "/",
    response_model=CompanyReadWithIncludes,
    status_code=status.HTTP_201_CREATED,
)
def create_company(
    company_in: CompanyCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> Company:
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no ID",
        )

    company = Company(
        name=company_in.name,
        company_type=company_in.company_type,
        created_by_user_id=current_user.id,
    )

    session.add(company)
    session.commit()
    session.refresh(company)
    return company


@router.get(
    "/",
    response_model=CompanyListResponse,
    status_code=status.HTTP_200_OK,
)
def list_companies(
    session: Session = Depends(get_session),
    _: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
    include: str | None = Query(default=None),
) -> Any:
    statement = select(Company)
    companies = session.exec(statement).all()
    if not companies:
        return CompanyListResponse(message="No records found")

    include_set = {
        item.strip()
        for item in (include or "").split(",")
        if item.strip()
    }

    if not include_set:
        return CompanyListResponse(
            items=[CompanyReadWithIncludes(**c.model_dump()) for c in companies]
        )

    results: list[CompanyReadWithIncludes] = []
    for company in companies:
        creator = None
        if "creator" in include_set:
            creator = session.get(User, company.created_by_user_id)
        blocks: list[CompanyBlock] = []
        if "blocks" in include_set and company.id is not None:
            blocks = session.exec(
                select(CompanyBlock).where(CompanyBlock.company_id == company.id)
            ).all()
        terminals: list[CompanyTerminal] = []
        if "terminals" in include_set and company.id is not None:
            terminals = session.exec(
                select(CompanyTerminal).where(
                    CompanyTerminal.owner_company_id == company.id
                )
            ).all()
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
)
def get_company(
    company_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
    include: str | None = Query(default=None),
):
    company = session.get(Company, company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    include_set = {
        item.strip()
        for item in (include or "").split(",")
        if item.strip()
    }
    if not include_set:
        return CompanyReadWithIncludes(**company.model_dump())

    creator = None
    if "creator" in include_set:
        creator = session.get(User, company.created_by_user_id)
    blocks: list[CompanyBlock] = []
    if "blocks" in include_set and company.id is not None:
        blocks = session.exec(
            select(CompanyBlock).where(CompanyBlock.company_id == company.id)
        ).all()
    terminals: list[CompanyTerminal] = []
    if "terminals" in include_set and company.id is not None:
        terminals = session.exec(
            select(CompanyTerminal).where(
                CompanyTerminal.owner_company_id == company.id
            )
        ).all()

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
)
def update_company(
    company_id: int,
    company_in: CompanyUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> CompanyReadWithIncludes:
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
)
def delete_company(
    company_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> CompanyDeleteResponse:
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
