from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import desc
from sqlmodel import Session, select

from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.company import Company
from app.models.company_terminal import CompanyTerminal
from app.models.enums import UserType
from app.models.external_analysis_record import (
    ExternalAnalysisRecord,
    ExternalAnalysisRecordCreate,
    ExternalAnalysisRecordListResponse,
    ExternalAnalysisRecordRead,
    ExternalAnalysisRecordUpdate,
)
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
from app.services.supabase_storage import upload_external_analysis_report

router = APIRouter(
    prefix="/external-analyses",
    tags=["External Analyses"],
)


def _require_id(value: int | None, label: str) -> int:
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{label} has no ID",
        )
    return value


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
    """Lista los tipos de análisis externo."""
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
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def create_external_analysis_type(
    payload: ExternalAnalysisTypeCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> ExternalAnalysisTypeRead:
    """Crea un tipo de análisis externo."""
    if current_user.id is None:
        raise HTTPException(status_code=500, detail="User has no ID")
    existing = session.exec(
        select(ExternalAnalysisType).where(ExternalAnalysisType.name == payload.name)
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
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def update_external_analysis_type(
    analysis_type_id: int,
    payload: ExternalAnalysisTypeUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> ExternalAnalysisTypeRead:
    """Actualiza un tipo de análisis externo por ID."""
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
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def delete_external_analysis_type(
    analysis_type_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> dict:
    """Elimina un tipo de análisis externo si no está en uso."""
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
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def list_terminal_external_analyses(
    terminal_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
) -> ExternalAnalysisTerminalListResponse:
    """Lista configuraciones de análisis externos por terminal."""
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
    config_by_type = {
        row.analysis_type_id: row
        for row in configs
        if row.analysis_type_id is not None
    }

    items: list[ExternalAnalysisTerminalRead] = []
    for analysis_type in types:
        if analysis_type.id is None:
            continue
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
            .order_by(desc(ExternalAnalysisRecord.performed_at))  # type: ignore[arg-type]
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
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def upsert_terminal_external_analysis(
    terminal_id: int,
    payload: ExternalAnalysisTerminalCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_role(UserType.admin, UserType.superadmin)),
) -> ExternalAnalysisTerminalRead:
    """Crea o actualiza la configuración de análisis externo por terminal."""
    if current_user.id is None:
        raise HTTPException(status_code=500, detail="User has no ID")
    terminal = session.get(CompanyTerminal, terminal_id)
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    analysis_type = session.get(ExternalAnalysisType, payload.analysis_type_id)
    if not analysis_type:
        raise HTTPException(status_code=404, detail="External analysis type not found")
    analysis_type_id = _require_id(analysis_type.id, "ExternalAnalysisType")

    row = session.exec(
        select(ExternalAnalysisTerminal).where(
            ExternalAnalysisTerminal.terminal_id == terminal_id,
            ExternalAnalysisTerminal.analysis_type_id == analysis_type_id,
        )
    ).first()
    if row:
        row.frequency_days = analysis_type.default_frequency_days
        row.is_active = payload.is_active
    else:
        row = ExternalAnalysisTerminal(
            terminal_id=terminal_id,
            analysis_type_id=analysis_type_id,
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
            ExternalAnalysisRecord.analysis_type_id == analysis_type_id,
        )
        .order_by(desc(ExternalAnalysisRecord.performed_at))  # type: ignore[arg-type]
    ).first()
    last_performed_at = last_record.performed_at if last_record else None
    next_due_at = (
        (last_performed_at + timedelta(days=row.frequency_days))
        if last_performed_at and row.frequency_days > 0
        else None
    )
    return ExternalAnalysisTerminalRead(
        terminal_id=terminal_id,
        analysis_type_id=analysis_type_id,
        analysis_type_name=analysis_type.name,
        frequency_days=row.frequency_days,
        is_active=row.is_active,
        last_performed_at=last_performed_at,
        next_due_at=next_due_at,
    )


@router.get(
    "/records/terminal/{terminal_id}",
    response_model=ExternalAnalysisRecordListResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def list_external_analysis_records(
    terminal_id: int,
    analysis_type_id: int | None = Query(
        default=None, description="Filtrar por tipo de análisis."
    ),
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
) -> ExternalAnalysisRecordListResponse:
    """
    Lista los registros de análisis externo de un terminal.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Parámetros:
    - `analysis_type_id`: filtra por tipo de análisis.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: terminal no encontrada.
    """
    terminal = session.get(CompanyTerminal, terminal_id)
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    _check_terminal_access(session, current_user, terminal_id)

    stmt = select(ExternalAnalysisRecord).where(
        ExternalAnalysisRecord.terminal_id == terminal_id
    )
    if analysis_type_id is not None:
        stmt = stmt.where(ExternalAnalysisRecord.analysis_type_id == analysis_type_id)
    rows = session.exec(
        stmt.order_by(desc(ExternalAnalysisRecord.performed_at))  # type: ignore[arg-type]
    ).all()
    if not rows:
        return ExternalAnalysisRecordListResponse(message="No records found")
    type_ids = {
        row.analysis_type_id for row in rows if row.analysis_type_id is not None
    }
    company_ids = {
        row.analysis_company_id for row in rows if row.analysis_company_id is not None
    }
    types = session.exec(
        select(ExternalAnalysisType).where(
            ExternalAnalysisType.id.in_(type_ids)  # type: ignore[union-attr]
        )
    ).all()
    type_by_id = {t.id: t for t in types}
    companies = (
        session.exec(
            select(Company).where(Company.id.in_(company_ids))  # type: ignore[union-attr]
        ).all()
        if company_ids
        else []
    )
    company_by_id = {c.id: c for c in companies}
    return ExternalAnalysisRecordListResponse(
        items=[
            ExternalAnalysisRecordRead(
                id=_require_id(row.id, "ExternalAnalysisRecord"),
                terminal_id=row.terminal_id,
                analysis_type_id=row.analysis_type_id,
                analysis_type_name=(
                    type_by_id[row.analysis_type_id].name
                    if row.analysis_type_id in type_by_id
                    else ""
                ),
                analysis_company_id=row.analysis_company_id,
                analysis_company_name=(
                    company_by_id[row.analysis_company_id].name
                    if row.analysis_company_id in company_by_id
                    else None
                ),
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
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def create_external_analysis_record(
    terminal_id: int,
    payload: ExternalAnalysisRecordCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
) -> ExternalAnalysisRecordRead:
    """
    Crea un registro de análisis externo para un terminal.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: terminal o tipo de análisis no encontrado.
    """
    if current_user.id is None:
        raise HTTPException(status_code=500, detail="User has no ID")
    terminal = session.get(CompanyTerminal, terminal_id)
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    _check_terminal_access(session, current_user, terminal_id)

    analysis_type = session.get(ExternalAnalysisType, payload.analysis_type_id)
    if not analysis_type:
        raise HTTPException(status_code=404, detail="External analysis type not found")

    analysis_company = None
    if payload.analysis_company_id is not None:
        analysis_company = session.get(Company, payload.analysis_company_id)
        if not analysis_company:
            raise HTTPException(status_code=404, detail="Company not found")

    performed_at = (
        _as_utc(payload.performed_at) if payload.performed_at else datetime.now(UTC)
    )
    record = ExternalAnalysisRecord(
        terminal_id=terminal_id,
        analysis_type_id=payload.analysis_type_id,
        analysis_company_id=payload.analysis_company_id,
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
    record_id = _require_id(record.id, "ExternalAnalysisRecord")
    return ExternalAnalysisRecordRead(
        id=record_id,
        terminal_id=record.terminal_id,
        analysis_type_id=record.analysis_type_id,
        analysis_type_name=analysis_type.name,
        analysis_company_id=record.analysis_company_id,
        analysis_company_name=analysis_company.name if analysis_company else None,
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
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def upload_external_analysis_report_file(
    record_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
) -> ExternalAnalysisRecordRead:
    """
    Sube el PDF del reporte para un registro de análisis externo.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: registro no encontrado.
    """
    record = session.get(ExternalAnalysisRecord, record_id)
    if not record:
        raise HTTPException(
            status_code=404, detail="External analysis record not found"
        )
    _check_terminal_access(session, current_user, record.terminal_id)

    report_url = upload_external_analysis_report(file, record_id)
    record.report_pdf_url = report_url
    session.add(record)
    session.commit()
    session.refresh(record)
    record_id = _require_id(record.id, "ExternalAnalysisRecord")

    analysis_type = session.get(ExternalAnalysisType, record.analysis_type_id)
    analysis_type_name = analysis_type.name if analysis_type else ""
    analysis_company_name = None
    if record.analysis_company_id is not None:
        analysis_company = session.get(Company, record.analysis_company_id)
        analysis_company_name = analysis_company.name if analysis_company else None
    return ExternalAnalysisRecordRead(
        id=record_id,
        terminal_id=record.terminal_id,
        analysis_type_id=record.analysis_type_id,
        analysis_type_name=analysis_type_name,
        analysis_company_id=record.analysis_company_id,
        analysis_company_name=analysis_company_name,
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


@router.patch(
    "/records/{record_id}",
    response_model=ExternalAnalysisRecordRead,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def update_external_analysis_record(
    record_id: int,
    payload: ExternalAnalysisRecordUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
) -> ExternalAnalysisRecordRead:
    """
    Actualiza un registro de análisis externo.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: registro no encontrado.
    """
    record = session.get(ExternalAnalysisRecord, record_id)
    if not record:
        raise HTTPException(
            status_code=404, detail="External analysis record not found"
        )
    _check_terminal_access(session, current_user, record.terminal_id)

    update_data = payload.model_dump(exclude_unset=True)
    if "analysis_type_id" in update_data:
        analysis_type = session.get(
            ExternalAnalysisType, update_data["analysis_type_id"]
        )
        if not analysis_type:
            raise HTTPException(
                status_code=404, detail="External analysis type not found"
            )
    if "analysis_company_id" in update_data:
        if update_data["analysis_company_id"] is not None:
            analysis_company = session.get(Company, update_data["analysis_company_id"])
            if not analysis_company:
                raise HTTPException(status_code=404, detail="Company not found")
        else:
            analysis_company = None
    else:
        analysis_company = None
    if "performed_at" in update_data and update_data["performed_at"] is not None:
        update_data["performed_at"] = _as_utc(update_data["performed_at"])

    for key, value in update_data.items():
        setattr(record, key, value)

    session.add(record)
    session.commit()
    session.refresh(record)
    record_id = _require_id(record.id, "ExternalAnalysisRecord")

    analysis_type = session.get(ExternalAnalysisType, record.analysis_type_id)
    analysis_type_name = analysis_type.name if analysis_type else ""
    analysis_company_name = None
    if record.analysis_company_id is not None:
        analysis_company = session.get(Company, record.analysis_company_id)
        analysis_company_name = analysis_company.name if analysis_company else None
    return ExternalAnalysisRecordRead(
        id=record_id,
        terminal_id=record.terminal_id,
        analysis_type_id=record.analysis_type_id,
        analysis_type_name=analysis_type_name,
        analysis_company_id=record.analysis_company_id,
        analysis_company_name=analysis_company_name,
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


@router.delete(
    "/records/{record_id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Recurso no encontrado"},
        status.HTTP_403_FORBIDDEN: {"description": "Permisos insuficientes"},
    },
)
def delete_external_analysis_record(
    record_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(
            UserType.visitor, UserType.user, UserType.admin, UserType.superadmin
        )
    ),
) -> dict:
    """
    Elimina un registro de análisis externo.

    Permisos: `visitor`, `user`, `admin`, `superadmin`.
    Respuestas:
    - 403: permisos insuficientes.
    - 404: registro no encontrado.
    """
    record = session.get(ExternalAnalysisRecord, record_id)
    if not record:
        raise HTTPException(
            status_code=404, detail="External analysis record not found"
        )
    _check_terminal_access(session, current_user, record.terminal_id)
    session.delete(record)
    session.commit()
    return {"message": "External analysis record deleted"}
