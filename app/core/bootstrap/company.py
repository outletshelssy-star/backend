from sqlmodel import Session, select

from app.core.bootstrap.data import (
    DEFAULT_BLOCKS,
    DEFAULT_COMPANIES,
    DEFAULT_PRIMARY_COMPANY_NAME,
    DEFAULT_TERMINALS,
    DEFAULT_USERS,
)
from app.core.security.password import hash_password
from app.models.company import Company
from app.models.company_block import CompanyBlock
from app.models.company_terminal import CompanyTerminal
from app.models.enums import CompanyType, UserType
from app.models.user import User
from app.models.user_terminal import UserTerminal


def ensure_default_company(session: Session) -> None:
    """
    Seed default companies, users, blocks, and terminals for development.
    """
    statement = select(User).where(User.user_type == UserType.superadmin)
    superadmin = session.exec(statement).first()

    if not superadmin or superadmin.id is None:
        raise RuntimeError("Superadmin must exist before creating company")

    for company_data in DEFAULT_COMPANIES:
        statement = select(Company).where(Company.name == company_data["name"])
        existing_company = session.exec(statement).first()
        if existing_company:
            continue
        new_company = Company(
            name=company_data["name"],
            company_type=CompanyType(company_data["company_type"]),
            created_by_user_id=superadmin.id,
        )
        session.add(new_company)
    session.commit()

    primary_company = session.exec(
        select(Company).where(Company.name == DEFAULT_PRIMARY_COMPANY_NAME)
    ).first()
    if not primary_company or primary_company.id is None:
        raise RuntimeError("Primary company must exist")

    secondary_company = session.exec(
        select(Company).where(Company.name != DEFAULT_PRIMARY_COMPANY_NAME)
    ).first()
    companies_by_name = {
        c.name: c
        for c in session.exec(select(Company)).all()
        if c.id is not None
    }

    if superadmin.company_id != primary_company.id:
        superadmin.company_id = primary_company.id
        session.add(superadmin)

    for user_data in DEFAULT_USERS:
        statement = select(User).where(User.email == user_data["email"])
        existing_user = session.exec(statement).first()
        if existing_user:
            target_company_name = user_data.get("company")
            target_company = (
                companies_by_name.get(target_company_name)
                if target_company_name
                else None
            )
            if target_company and existing_user.company_id != target_company.id:
                existing_user.company_id = target_company.id
                session.add(existing_user)
            elif existing_user.user_type in {
                UserType.superadmin,
                UserType.admin,
            }:
                if existing_user.company_id != primary_company.id:
                    existing_user.company_id = primary_company.id
                    session.add(existing_user)
            elif secondary_company and existing_user.company_id != secondary_company.id:
                existing_user.company_id = secondary_company.id
                session.add(existing_user)
            continue

        target_company_name = user_data.get("company")
        target_company = (
            companies_by_name.get(target_company_name)
            if target_company_name
            else None
        )
        new_user = User(
            name=user_data["name"],
            last_name=user_data["last_name"],
            email=user_data["email"],
            user_type=UserType(user_data["user_type"]),
            is_active=True,
            password_hash=hash_password(user_data["password"]),
            company_id=(
                target_company.id
                if target_company
                else (
                    primary_company.id
                    if user_data["user_type"] in {"superadmin", "admin"}
                    else (secondary_company.id if secondary_company else primary_company.id)
                )
            ),
        )
        session.add(new_user)

    session.commit()

    blocks = session.exec(
        select(CompanyBlock).where(CompanyBlock.company_id == primary_company.id)
    ).all()
    existing_names = {b.name for b in blocks}
    for name in DEFAULT_BLOCKS:
        if name in existing_names:
            continue
        new_block = CompanyBlock(
            name=name,
            is_active=True,
            company_id=primary_company.id,
            created_by_user_id=superadmin.id,
        )
        session.add(new_block)
    session.commit()

    block = session.exec(
        select(CompanyBlock).where(
            CompanyBlock.company_id == primary_company.id,
            CompanyBlock.name == DEFAULT_BLOCKS[0],
        )
    ).first()
    if not block or block.id is None:
        raise RuntimeError("Default block must exist for terminal creation")

    blocks_by_name = {
        b.name: b
        for b in session.exec(
            select(CompanyBlock).where(CompanyBlock.company_id == primary_company.id)
        ).all()
        if b.id is not None
    }

    terminals = session.exec(
        select(CompanyTerminal).where(
            CompanyTerminal.owner_company_id == primary_company.id
        )
    ).all()
    existing_terminals = {t.name for t in terminals}
    terminal_codes_by_name = {t.name: t for t in terminals}

    for terminal_data in DEFAULT_TERMINALS:
        name = terminal_data["name"]
        block_name = terminal_data["block"]
        code = terminal_data.get("code")
        if name in existing_terminals:
            existing_terminal = terminal_codes_by_name.get(name)
            if existing_terminal and not existing_terminal.terminal_code and code:
                existing_terminal.terminal_code = code
                session.add(existing_terminal)
            continue
        block_for_terminal = blocks_by_name.get(block_name)
        if not block_for_terminal or block_for_terminal.id is None:
            raise RuntimeError(f"Block '{block_name}' not found for terminal '{name}'")
        new_terminal = CompanyTerminal(
            name=name,
            is_active=True,
            block_id=block_for_terminal.id,
            owner_company_id=primary_company.id,
            admin_company_id=primary_company.id,
            created_by_user_id=superadmin.id,
            terminal_code=code,
        )
        session.add(new_terminal)

    session.commit()

    terminals = session.exec(
        select(CompanyTerminal).where(
            CompanyTerminal.owner_company_id == primary_company.id
        )
    ).all()
    terminals_by_name = {t.name: t for t in terminals if t.id is not None}
    if terminals_by_name:
        users_by_email = {
            u.email: u
            for u in session.exec(
                select(User).where(User.email.in_([u["email"] for u in DEFAULT_USERS]))
            ).all()
        }
        existing_links = session.exec(
            select(UserTerminal).where(
                UserTerminal.user_id.in_(
                    [u.id for u in users_by_email.values() if u.id]
                )
            )
        ).all()
        existing_pairs = {
            (link.user_id, link.terminal_id) for link in existing_links
        }
        for user_data in DEFAULT_USERS:
            terminals_for_user = user_data.get("terminals") or []
            if not terminals_for_user:
                continue
            user = users_by_email.get(user_data["email"])
            if not user or user.id is None:
                continue
            for terminal_name in terminals_for_user:
                terminal = terminals_by_name.get(terminal_name)
                if not terminal or terminal.id is None:
                    continue
                pair = (user.id, terminal.id)
                if pair in existing_pairs:
                    continue
                session.add(UserTerminal(user_id=user.id, terminal_id=terminal.id))
        session.commit()
