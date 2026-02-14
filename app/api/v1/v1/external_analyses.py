from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlmodel import Session, delete, select

from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.company_terminal import CompanyTerminal
from app.models.external_analysis_record import (
    ExternalAnalysisRecord,
    ExternalAnalysisRecordCreate,
    ExternalAnalysisRecordListResponse,
    ExternalAnalysisRecordRead,
)
from app.services.supabase_storage import upload_external_analysis_report
from app.models.external_analysis_terminal import (
    ExternalAnalysisTerminal,
    ExternalAnalysisTerminalCreate,
    ExternalAnalysisTerminalListResponse,
    ExternalAnalysisTerminalRead,
)
from app.models.external_analysis_type import (
    ExternalAnalysisType,
    ExternalAnalysisTypeCreate,
    ExternalAnalysisTypeListResponse,
    ExternalAnalysisTypeRead,
    ExternalAnalysisTypeUpdate,
)
from app.models.user import User
from app.models.user_terminal import UserTerminal
from app.models.enums import UserType

router = APIRouter(
    prefix="/external-analyses",
    tags=["External Analyses"],
)


def _as_utc(dt_value: datetime) -> datetime:
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=UTC)
    return dt_value.astimezone(UTC)


def _check_terminal_access(session: Session, user: User, terminal_id: int) -> None:
    if user.user_type == UserType.superadmin:
        return
    allowed_terminal_ids = session.exec(
        select(UserTerminal.terminal_id).where(UserTerminal.user_id == user.id)
    ).all()
    if allowed_terminal_ids and terminal_id not in set(allowed_terminal_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this terminal",
        )


@router.get(
    "/types",
    response_model=ExternalAnalysisTypeListResponse,
)
def list_external_analysis_types(
    session: Session = Depends(get_session),
) -> ExternalAnalysisTypeListResponse:
    rows = session.exec(select(ExternalAnalysisType)).all()
    if not rows:
        return ExternalAnalysisTypeListResponse(message="No records found")
    return ExternalAnalysisTypeListResponse(
        items=[ExternalAnalysisTypeRead(**row.model_dump()) for row in rows]
    )


@router.post(
    "/types",
    response_model=ExternalAnalysisTypeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_external_analysis_type(
    payload: ExternalAnalysisTypeCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> ExternalAnalysisTypeRead:
    if current_user.id is None:
        raise HTTPException(status_code=500, detail="User has no ID")
    existing = session.exec(
        select(ExternalAnalysisType).where(
            ExternalAnalysisType.name == payload.name
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="External analysis type already exists",
        )
    row = ExternalAnalysisType(
        name=payload.name,
        default_frequency_days=payload.default_frequency_days,
        is_active=payload.is_active,
        created_by_user_id=current_user.id,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return ExternalAnalysisTypeRead(**row.model_dump())


@router.patch(
    "/types/{analysis_type_id}",
    response_model=ExternalAnalysisTypeRead,
)
def update_external_analysis_type(
    analysis_type_id: int,
    payload: ExternalAnalysisTypeUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> ExternalAnalysisTypeRead:
    row = session.get(ExternalAnalysisType, analysis_type_id)
    if not row:
        raise HTTPException(status_code=404, detail="External analysis type not found")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(row, key, value)
    session.add(row)
    session.commit()
    session.refresh(row)
    return ExternalAnalysisTypeRead(**row.model_dump())


@router.delete(
    "/types/{analysis_type_id}",
    status_code=status.HTTP_200_OK,
)
def delete_external_analysis_type(
    analysis_type_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> dict:
    row = session.get(ExternalAnalysisType, analysis_type_id)
    if not row:
        raise HTTPException(status_code=404, detail="External analysis type not found")
    in_use = session.exec(
        select(ExternalAnalysisTerminal).where(
            ExternalAnalysisTerminal.analysis_type_id == analysis_type_id
        )
    ).first()
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="External analysis type is in use",
        )
    session.delete(row)
    session.commit()
    return {"message": "External analysis type deleted"}


@router.get(
    "/terminal/{terminal_id}",
    response_model=ExternalAnalysisTerminalListResponse,
)
def list_terminal_external_analyses(
    terminal_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.visitor, UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> ExternalAnalysisTerminalListResponse:
    terminal = session.get(CompanyTerminal, terminal_id)
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    _check_terminal_access(session, current_user, terminal_id)

    types = session.exec(select(ExternalAnalysisType)).all()
    configs = session.exec(
        select(ExternalAnalysisTerminal).where(
            ExternalAnalysisTerminal.terminal_id == terminal_id
        )
    ).all()
    config_by_type = {row.analysis_type_id: row for row in configs}

    items: list[ExternalAnalysisTerminalRead] = []
    for analysis_type in types:
        cfg = config_by_type.get(analysis_type.id)
        frequency_days = (
            cfg.frequency_days
            if cfg is not None
            and cfg.frequency_days is not None
            and cfg.frequency_days > 0
            else analysis_type.default_frequency_days
        )
        is_active = cfg.is_active if cfg is not None else analysis_type.is_active
        last_record = session.exec(
            select(ExternalAnalysisRecord)
            .where(
                ExternalAnalysisRecord.terminal_id == terminal_id,
                ExternalAnalysisRecord.analysis_type_id == analysis_type.id,
            )
            .order_by(ExternalAnalysisRecord.performed_at.desc())
        ).first()
        last_performed_at = last_record.performed_at if last_record else None
        next_due_at = (
            (last_performed_at + timedelta(days=frequency_days))
            if last_performed_at and frequency_days > 0
            else None
        )
        items.append(
            ExternalAnalysisTerminalRead(
                terminal_id=terminal_id,
                analysis_type_id=analysis_type.id,
                analysis_type_name=analysis_type.name,
                frequency_days=frequency_days,
                is_active=is_active,
                last_performed_at=last_performed_at,
                next_due_at=next_due_at,
            )
        )
    if not items:
        return ExternalAnalysisTerminalListResponse(message="No records found")
    return ExternalAnalysisTerminalListResponse(items=items)


@router.post(
    "/terminal/{terminal_id}",
    response_model=ExternalAnalysisTerminalRead,
)
def upsert_terminal_external_analysis(
    terminal_id: int,
    payload: ExternalAnalysisTerminalCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> ExternalAnalysisTerminalRead:
    if current_user.id is None:
        raise HTTPException(status_code=500, detail="User has no ID")
    terminal = session.get(CompanyTerminal, terminal_id)
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    analysis_type = session.get(ExternalAnalysisType, payload.analysis_type_id)
    if not analysis_type:
        raise HTTPException(status_code=404, detail="External analysis type not found")

    row = session.exec(
        select(ExternalAnalysisTerminal).where(
            ExternalAnalysisTerminal.terminal_id == terminal_id,
            ExternalAnalysisTerminal.analysis_type_id == payload.analysis_type_id,
        )
    ).first()
    if row:
        row.frequency_days = analysis_type.default_frequency_days
        row.is_active = payload.is_active
    else:
        row = ExternalAnalysisTerminal(
            terminal_id=terminal_id,
            analysis_type_id=payload.analysis_type_id,
            frequency_days=analysis_type.default_frequency_days,
            is_active=payload.is_active,
            created_by_user_id=current_user.id,
        )
    session.add(row)
    session.commit()
    session.refresh(row)

    last_record = session.exec(
        select(ExternalAnalysisRecord)
        .where(
            ExternalAnalysisRecord.terminal_id == terminal_id,
            ExternalAnalysisRecord.analysis_type_id == payload.analysis_type_id,
        )
        .order_by(ExternalAnalysisRecord.performed_at.desc())
    ).first()
    last_performed_at = last_record.performed_at if last_record else None
    next_due_at = (
        (last_performed_at + timedelta(days=row.frequency_days))
        if last_performed_at and row.frequency_days > 0
        else None
    )
    return ExternalAnalysisTerminalRead(
        terminal_id=terminal_id,
        analysis_type_id=payload.analysis_type_id,
        analysis_type_name=analysis_type.name,
        frequency_days=row.frequency_days,
        is_active=row.is_active,
        last_performed_at=last_performed_at,
        next_due_at=next_due_at,
    )


@router.get(
    "/records/terminal/{terminal_id}",
    response_model=ExternalAnalysisRecordListResponse,
)
def list_external_analysis_records(
    terminal_id: int,
    analysis_type_id: int | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.visitor, UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> ExternalAnalysisRecordListResponse:
    terminal = session.get(CompanyTerminal, terminal_id)
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    _check_terminal_access(session, current_user, terminal_id)

    stmt = select(ExternalAnalysisRecord).where(
        ExternalAnalysisRecord.terminal_id == terminal_id
    )
    if analysis_type_id is not None:
        stmt = stmt.where(ExternalAnalysisRecord.analysis_type_id == analysis_type_id)
    rows = session.exec(stmt.order_by(ExternalAnalysisRecord.performed_at.desc())).all()
    if not rows:
        return ExternalAnalysisRecordListResponse(message="No records found")
    type_ids = {row.analysis_type_id for row in rows}
    types = session.exec(
        select(ExternalAnalysisType).where(ExternalAnalysisType.id.in_(type_ids))
    ).all()
    type_by_id = {t.id: t for t in types}
    return ExternalAnalysisRecordListResponse(
        items=[
            ExternalAnalysisRecordRead(
                id=row.id,
                terminal_id=row.terminal_id,
                analysis_type_id=row.analysis_type_id,
                analysis_type_name=type_by_id.get(row.analysis_type_id).name
                if type_by_id.get(row.analysis_type_id)
                else "",
                performed_at=row.performed_at,
                report_number=row.report_number,
                report_pdf_url=row.report_pdf_url,
                result_value=row.result_value,
                result_unit=row.result_unit,
                result_uncertainty=row.result_uncertainty,
                method=row.method,
                notes=row.notes,
                created_by_user_id=row.created_by_user_id,
            )
            for row in rows
        ]
    )


@router.post(
    "/records/terminal/{terminal_id}",
    response_model=ExternalAnalysisRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def create_external_analysis_record(
    terminal_id: int,
    payload: ExternalAnalysisRecordCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.visitor, UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> ExternalAnalysisRecordRead:
    if current_user.id is None:
        raise HTTPException(status_code=500, detail="User has no ID")
    terminal = session.get(CompanyTerminal, terminal_id)
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    _check_terminal_access(session, current_user, terminal_id)

    analysis_type = session.get(ExternalAnalysisType, payload.analysis_type_id)
    if not analysis_type:
        raise HTTPException(status_code=404, detail="External analysis type not found")

    performed_at = _as_utc(payload.performed_at) if payload.performed_at else datetime.now(UTC)
    record = ExternalAnalysisRecord(
        terminal_id=terminal_id,
        analysis_type_id=payload.analysis_type_id,
        performed_at=performed_at,
        report_number=payload.report_number,
        result_value=payload.result_value,
        result_unit=payload.result_unit,
        result_uncertainty=payload.result_uncertainty,
        method=payload.method,
        notes=payload.notes,
        created_by_user_id=current_user.id,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return ExternalAnalysisRecordRead(
        id=record.id,
        terminal_id=record.terminal_id,
        analysis_type_id=record.analysis_type_id,
        analysis_type_name=analysis_type.name,
        performed_at=record.performed_at,
        report_number=record.report_number,
        report_pdf_url=record.report_pdf_url,
        result_value=record.result_value,
        result_unit=record.result_unit,
        result_uncertainty=record.result_uncertainty,
        method=record.method,
        notes=record.notes,
        created_by_user_id=record.created_by_user_id,
    )


@router.post(
    "/records/{record_id}/report",
    response_model=ExternalAnalysisRecordRead,
)
def upload_external_analysis_report_file(
    record_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.visitor, UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> ExternalAnalysisRecordRead:
    record = session.get(ExternalAnalysisRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="External analysis record not found")
    _check_terminal_access(session, current_user, record.terminal_id)

    report_url = upload_external_analysis_report(file, record_id)
    record.report_pdf_url = report_url
    session.add(record)
    session.commit()
    session.refresh(record)

    analysis_type = session.get(ExternalAnalysisType, record.analysis_type_id)
    analysis_type_name = analysis_type.name if analysis_type else ""
    return ExternalAnalysisRecordRead(
        id=record.id,
        terminal_id=record.terminal_id,
        analysis_type_id=record.analysis_type_id,
        analysis_type_name=analysis_type_name,
        performed_at=record.performed_at,
        report_number=record.report_number,
        report_pdf_url=record.report_pdf_url,
        result_value=record.result_value,
        result_unit=record.result_unit,
        result_uncertainty=record.result_uncertainty,
        method=record.method,
        notes=record.notes,
        created_by_user_id=record.created_by_user_id,
    )
