from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Any
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
from app.models.user import User

router = APIRouter(
    prefix="/company-blocks",
    tags=["Company Blocks"],
)


@router.post(
    "/",
    response_model=CompanyBlockReadWithIncludes,
    status_code=status.HTTP_201_CREATED,
)
def create_company_block(
    block_in: CompanyBlockCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> CompanyBlock:
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
        company_id=company.id,
        created_by_user_id=current_user.id,
    )

    session.add(block)
    session.commit()
    session.refresh(block)
    return block


@router.get(
    "/",
    response_model=CompanyBlockListResponse,
    status_code=status.HTTP_200_OK,
)
def list_company_blocks(
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
    include: str | None = Query(default=None),
    company_id: int | None = Query(default=None),
) -> Any:
    statement = select(CompanyBlock)
    if company_id is not None:
        statement = statement.where(CompanyBlock.company_id == company_id)
    blocks = session.exec(statement).all()
    if not blocks:
        return CompanyBlockListResponse(message="No records found")
    include_set = {
        item.strip()
        for item in (include or "").split(",")
        if item.strip()
    }
    if not include_set:
        return CompanyBlockListResponse(
            items=[CompanyBlockReadWithIncludes(**b.model_dump()) for b in blocks]
        )

    results: list[CompanyBlockReadWithIncludes] = []
    for block in blocks:
        block_company = None
        if "company" in include_set:
            block_company = session.get(Company, block.company_id)
        creator = None
        if "creator" in include_set:
            creator = session.get(User, block.created_by_user_id)
        terminals: list[CompanyTerminal] = []
        if "terminals" in include_set and block.id is not None:
            terminals = session.exec(
                select(CompanyTerminal).where(
                    CompanyTerminal.block_id == block.id
                )
            ).all()
        results.append(
            CompanyBlockReadWithIncludes(
                **block.model_dump(),
                company=block_company,
                creator=creator,
                terminals=terminals,
            )
        )
    return CompanyBlockListResponse(items=results)


@router.get(
    "/{block_id}",
    response_model=CompanyBlockReadWithIncludes,
    status_code=status.HTTP_200_OK,
)
def get_company_block(
    block_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
    include: str | None = Query(default=None),
    company_id: int = Query(...),
):
    block = session.get(CompanyBlock, block_id)
    if not block or block.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company block not found",
        )
    include_set = {
        item.strip()
        for item in (include or "").split(",")
        if item.strip()
    }
    if not include_set:
        return CompanyBlockReadWithIncludes(**block.model_dump())

    block_company = None
    if "company" in include_set:
        block_company = session.get(Company, block.company_id)
    creator = None
    if "creator" in include_set:
        creator = session.get(User, block.created_by_user_id)
    terminals: list[CompanyTerminal] = []
    if "terminals" in include_set and block.id is not None:
        terminals = session.exec(
            select(CompanyTerminal).where(CompanyTerminal.block_id == block.id)
        ).all()
    return CompanyBlockReadWithIncludes(
        **block.model_dump(),
        company=block_company,
        creator=creator,
        terminals=terminals,
    )


@router.put(
    "/{block_id}",
    response_model=CompanyBlockReadWithIncludes,
    status_code=status.HTTP_200_OK,
)
def update_company_block(
    block_id: int,
    block_in: CompanyBlockUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> CompanyBlockReadWithIncludes:
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
)
def delete_company_block(
    block_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> CompanyBlockDeleteResponse:
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
