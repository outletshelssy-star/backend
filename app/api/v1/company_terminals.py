from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Any
from sqlmodel import Session, select, delete

from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.company import Company
from app.models.company_block import CompanyBlock
from app.models.company_terminal import (
    CompanyTerminal,
    CompanyTerminalCreate,
    CompanyTerminalDeleteResponse,
    CompanyTerminalListResponse,
    CompanyTerminalReadWithIncludes,
    CompanyTerminalUpdate,
)
from app.models.external_analysis_record import ExternalAnalysisRecord
from app.models.external_analysis_terminal import ExternalAnalysisTerminal
from app.models.enums import UserType
from app.models.user import User
from app.models.user_terminal import UserTerminal

router = APIRouter(
    prefix="/company-terminals",
    tags=["Company Terminals"],
)


@router.post(
    "/",
    response_model=CompanyTerminalReadWithIncludes,
    status_code=status.HTTP_201_CREATED,
)
def create_company_terminal(
    terminal_in: CompanyTerminalCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> CompanyTerminal:
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no ID",
        )

    owner_company = session.get(Company, terminal_in.owner_company_id)
    if not owner_company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner company not found",
        )

    block = session.get(CompanyBlock, terminal_in.block_id)
    if not block or block.company_id != owner_company.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company block not found",
        )

    admin_company = session.get(Company, terminal_in.admin_company_id)
    if not admin_company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin company not found",
        )

    if terminal_in.has_lab and terminal_in.lab_terminal_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lab_terminal_id must be empty when has_lab is true",
        )
    if not terminal_in.has_lab and terminal_in.lab_terminal_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lab_terminal_id is required when has_lab is false",
        )
    if terminal_in.lab_terminal_id is not None:
        lab_terminal = session.get(CompanyTerminal, terminal_in.lab_terminal_id)
        if not lab_terminal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lab terminal not found",
            )
        if not lab_terminal.has_lab:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lab terminal must have its own lab",
            )
        if lab_terminal.owner_company_id != owner_company.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lab terminal must belong to the same owner company",
            )

    terminal = CompanyTerminal(
        name=terminal_in.name,
        is_active=terminal_in.is_active,
        has_lab=terminal_in.has_lab,
        lab_terminal_id=terminal_in.lab_terminal_id,
        block_id=terminal_in.block_id,
        owner_company_id=owner_company.id,
        admin_company_id=terminal_in.admin_company_id,
        created_by_user_id=current_user.id,
        terminal_code=terminal_in.terminal_code,
    )

    session.add(terminal)
    session.commit()
    session.refresh(terminal)
    return terminal


@router.get(
    "/",
    response_model=CompanyTerminalListResponse,
    status_code=status.HTTP_200_OK,
)
def list_company_terminals(
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.visitor, UserType.user, UserType.admin, UserType.superadmin)
    ),
    include: str | None = Query(default=None),
    owner_company_id: int | None = Query(default=None),
) -> Any:
    statement = select(CompanyTerminal)
    if owner_company_id is not None:
        statement = statement.where(
            CompanyTerminal.owner_company_id == owner_company_id
        )
    if current_user.user_type != UserType.superadmin:
        allowed_terminal_ids = session.exec(
            select(UserTerminal.terminal_id).where(
                UserTerminal.user_id == current_user.id
            )
        ).all()
        if allowed_terminal_ids:
            statement = statement.where(
                CompanyTerminal.id.in_(allowed_terminal_ids)
            )
    terminals = session.exec(statement).all()
    if not terminals:
        return CompanyTerminalListResponse(message="No records found")

    include_set = {
        item.strip()
        for item in (include or "").split(",")
        if item.strip()
    }
    if not include_set:
        return CompanyTerminalListResponse(
            items=[CompanyTerminalReadWithIncludes(**t.model_dump()) for t in terminals]
        )

    results: list[CompanyTerminalReadWithIncludes] = []
    for terminal in terminals:
        block = None
        if "block" in include_set:
            block = session.get(CompanyBlock, terminal.block_id)
        owner_company_obj = None
        if "owner_company" in include_set:
            owner_company_obj = session.get(Company, terminal.owner_company_id)
        admin_company_obj = None
        if "admin_company" in include_set:
            admin_company_obj = session.get(Company, terminal.admin_company_id)
        creator = None
        if "creator" in include_set:
            creator = session.get(User, terminal.created_by_user_id)
        results.append(
            CompanyTerminalReadWithIncludes(
                **terminal.model_dump(),
                block=block,
                owner_company=owner_company_obj,
                admin_company=admin_company_obj,
                creator=creator,
            )
        )
    return CompanyTerminalListResponse(items=results)


@router.get(
    "/{terminal_id}",
    response_model=CompanyTerminalReadWithIncludes,
    status_code=status.HTTP_200_OK,
)
def get_company_terminal(
    terminal_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.visitor, UserType.user, UserType.admin, UserType.superadmin)
    ),
    include: str | None = Query(default=None),
    owner_company_id: int = Query(...),
):
    if current_user.user_type != UserType.superadmin:
        allowed_terminal_ids = session.exec(
            select(UserTerminal.terminal_id).where(
                UserTerminal.user_id == current_user.id
            )
        ).all()
        if allowed_terminal_ids and terminal_id not in allowed_terminal_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company terminal not found",
            )
    terminal = session.get(CompanyTerminal, terminal_id)
    if not terminal or terminal.owner_company_id != owner_company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company terminal not found",
        )
    include_set = {
        item.strip()
        for item in (include or "").split(",")
        if item.strip()
    }
    if not include_set:
        return CompanyTerminalReadWithIncludes(**terminal.model_dump())

    block = None
    if "block" in include_set:
        block = session.get(CompanyBlock, terminal.block_id)
    owner_company_obj = None
    if "owner_company" in include_set:
        owner_company_obj = session.get(Company, terminal.owner_company_id)
    admin_company_obj = None
    if "admin_company" in include_set:
        admin_company_obj = session.get(Company, terminal.admin_company_id)
    creator = None
    if "creator" in include_set:
        creator = session.get(User, terminal.created_by_user_id)

    return CompanyTerminalReadWithIncludes(
        **terminal.model_dump(),
        block=block,
        owner_company=owner_company_obj,
        admin_company=admin_company_obj,
        creator=creator,
    )


@router.put(
    "/{terminal_id}",
    response_model=CompanyTerminalReadWithIncludes,
    status_code=status.HTTP_200_OK,
)
def update_company_terminal(
    terminal_id: int,
    terminal_in: CompanyTerminalUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> CompanyTerminalReadWithIncludes:
    terminal = session.get(CompanyTerminal, terminal_id)
    if not terminal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company terminal not found",
        )

    update_data = terminal_in.model_dump(exclude_unset=True)

    owner_company_id = update_data.get(
        "owner_company_id", terminal.owner_company_id
    )
    block_id = update_data.get("block_id", terminal.block_id)
    admin_company_id = update_data.get(
        "admin_company_id", terminal.admin_company_id
    )

    owner_company = session.get(Company, owner_company_id)
    if not owner_company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner company not found",
        )

    block = session.get(CompanyBlock, block_id)
    if not block or block.company_id != owner_company.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company block not found",
        )

    admin_company = session.get(Company, admin_company_id)
    if not admin_company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin company not found",
        )

    if update_data.get("has_lab") is True and "lab_terminal_id" not in update_data:
        update_data["lab_terminal_id"] = None

    has_lab = update_data.get("has_lab", terminal.has_lab)
    lab_terminal_id = update_data.get("lab_terminal_id", terminal.lab_terminal_id)

    if has_lab and lab_terminal_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lab_terminal_id must be empty when has_lab is true",
        )
    if not has_lab and lab_terminal_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lab_terminal_id is required when has_lab is false",
        )
    if lab_terminal_id is not None:
        if lab_terminal_id == terminal.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lab terminal cannot reference itself",
            )
        lab_terminal = session.get(CompanyTerminal, lab_terminal_id)
        if not lab_terminal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lab terminal not found",
            )
        if not lab_terminal.has_lab:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lab terminal must have its own lab",
            )
        if lab_terminal.owner_company_id != owner_company.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lab terminal must belong to the same owner company",
            )

    for field, value in update_data.items():
        setattr(terminal, field, value)

    session.add(terminal)
    session.commit()
    session.refresh(terminal)
    return CompanyTerminalReadWithIncludes(**terminal.model_dump())


@router.delete(
    "/{terminal_id}",
    response_model=CompanyTerminalDeleteResponse,
    status_code=status.HTTP_200_OK,
)
def delete_company_terminal(
    terminal_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> CompanyTerminalDeleteResponse:
    terminal = session.get(CompanyTerminal, terminal_id)
    if not terminal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company terminal not found",
        )

    terminal_data = CompanyTerminalReadWithIncludes(**terminal.model_dump())
    session.exec(
        delete(ExternalAnalysisRecord).where(
            ExternalAnalysisRecord.terminal_id == terminal_id
        )
    )
    session.exec(
        delete(ExternalAnalysisTerminal).where(
            ExternalAnalysisTerminal.terminal_id == terminal_id
        )
    )
    session.exec(
        delete(UserTerminal).where(UserTerminal.terminal_id == terminal_id)
    )
    session.delete(terminal)
    session.commit()
    return CompanyTerminalDeleteResponse(
        action="deleted",
        message="Company terminal deleted successfully.",
        terminal=terminal_data,
    )
