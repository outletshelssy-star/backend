from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func, delete

from app.core.security.authorization import require_role
from app.db.session import get_session
from app.models.company_terminal import CompanyTerminal
from app.models.enums import SampleAnalysisType, UserType
from app.models.sample import (
    Sample,
    SampleAnalysis,
    SampleAnalysisCreate,
    SampleAnalysisHistory,
    SampleAnalysisRead,
    SampleCreate,
    SampleListResponse,
    SampleRead,
    SampleUpdate,
)
from app.models.user import User
from app.models.user_terminal import UserTerminal
from app.utils.hydrometer import api_60f_crude

router = APIRouter(prefix="/samples", tags=["Samples"])


def _as_utc(dt_value: datetime) -> datetime:
    if dt_value.tzinfo is None:
        return dt_value.replace(tzinfo=UTC)
    return dt_value.astimezone(UTC)


def _terminal_code(name: str, terminal_code: str | None = None) -> str:
    if terminal_code:
        normalized = " ".join(str(terminal_code).strip().upper().split())
        if normalized:
            return normalized
    cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in name)
    parts = [p for p in cleaned.strip().split() if p]
    if not parts:
        return "TRM"
    if len(parts) >= 3:
        return "".join(p[0].upper() for p in parts[:3])
    token = parts[0].upper()
    return token[:3]


def _check_terminal_access(
    session: Session,
    user: User,
    terminal_id: int,
) -> None:
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


def _build_analysis(
    analysis: SampleAnalysisCreate,
) -> SampleAnalysis:
    if analysis.analysis_type not in {
        SampleAnalysisType.api_astm_1298,
        SampleAnalysisType.water_astm_4377,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported analysis type",
        )
    api_60f = None
    if analysis.analysis_type == SampleAnalysisType.api_astm_1298:
        if analysis.temp_obs_f is None or analysis.lectura_api is None:
            api_60f = None
        else:
            api_60f = api_60f_crude(analysis.temp_obs_f, analysis.lectura_api)
    return SampleAnalysis(
        analysis_type=analysis.analysis_type,
        product_name=analysis.product_name or "Crudo",
        temp_obs_f=analysis.temp_obs_f,
        lectura_api=analysis.lectura_api,
        api_60f=api_60f,
        hydrometer_id=analysis.hydrometer_id,
        thermometer_id=analysis.thermometer_id,
        water_value=analysis.water_value,
    )


@router.post(
    "/",
    response_model=SampleRead,
    status_code=status.HTTP_201_CREATED,
)
def create_sample(
    payload: SampleCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> SampleRead:
    if current_user.id is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User has no ID",
        )
    terminal = session.exec(
        select(CompanyTerminal)
        .where(CompanyTerminal.id == payload.terminal_id)
        .with_for_update()
    ).first()
    if not terminal or terminal.id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Terminal not found",
        )
    _check_terminal_access(session, current_user, terminal.id)

    seq = terminal.next_sample_sequence or 1
    terminal.next_sample_sequence = seq + 1
    session.add(terminal)
    session.commit()
    session.refresh(terminal)

    code = f"{_terminal_code(terminal.name, terminal.terminal_code)}-{seq:04d}"
    sample = Sample(
        terminal_id=terminal.id,
        code=code,
        sequence=seq,
        created_by_user_id=current_user.id,
        product_name="Crudo",
        identifier=payload.identifier,
    )
    session.add(sample)
    session.commit()
    session.refresh(sample)

    analysis_rows: list[SampleAnalysis] = []
    for analysis in payload.analyses:
        row = _build_analysis(analysis)
        row.sample_id = sample.id
        analysis_rows.append(row)
        session.add(row)
    session.commit()

    return SampleRead(
        id=sample.id,
        terminal_id=sample.terminal_id,
        code=sample.code,
        sequence=sample.sequence,
        created_by_user_id=sample.created_by_user_id,
        created_at=sample.created_at,
        identifier=sample.identifier,
        product_name=sample.product_name,
        analyzed_at=sample.analyzed_at,
        lab_humidity=sample.lab_humidity,
        lab_temperature=sample.lab_temperature,
        analyses=[
            SampleAnalysisRead.model_validate(r, from_attributes=True)
            for r in analysis_rows
        ],
    )


@router.get(
    "/terminal/{terminal_id}",
    response_model=SampleListResponse,
    status_code=status.HTTP_200_OK,
)
def list_samples(
    terminal_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.visitor, UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> SampleListResponse:
    _check_terminal_access(session, current_user, terminal_id)
    samples = session.exec(
        select(Sample)
        .where(Sample.terminal_id == terminal_id)
        .order_by(Sample.created_at)
    ).all()
    if not samples:
        return SampleListResponse(message="No records found")

    items: list[SampleRead] = []
    for sample in samples:
        analyses = session.exec(
            select(SampleAnalysis).where(SampleAnalysis.sample_id == sample.id)
        ).all()
        items.append(
            SampleRead(
                id=sample.id,
                terminal_id=sample.terminal_id,
                code=sample.code,
                sequence=sample.sequence,
                created_by_user_id=sample.created_by_user_id,
                created_at=_as_utc(sample.created_at),
                identifier=sample.identifier,
                product_name=sample.product_name,
                analyzed_at=_as_utc(sample.analyzed_at) if sample.analyzed_at else None,
                lab_humidity=sample.lab_humidity,
                lab_temperature=sample.lab_temperature,
                analyses=[
                    SampleAnalysisRead.model_validate(r, from_attributes=True)
                    for r in analyses
                ],
            )
        )
    return SampleListResponse(items=items)


@router.patch(
    "/{sample_id}",
    response_model=SampleRead,
    status_code=status.HTTP_200_OK,
)
def update_sample(
    sample_id: int,
    payload: SampleUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> SampleRead:
    sample = session.get(Sample, sample_id)
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found",
        )
    _check_terminal_access(session, current_user, sample.terminal_id)

    if payload.product_name is not None:
        sample.product_name = payload.product_name
    if payload.analyzed_at is not None:
        sample.analyzed_at = _as_utc(payload.analyzed_at)
    if payload.lab_humidity is not None:
        sample.lab_humidity = payload.lab_humidity
    if payload.lab_temperature is not None:
        sample.lab_temperature = payload.lab_temperature
    if payload.identifier is not None:
        sample.identifier = payload.identifier

    analysis_rows: list[SampleAnalysis] = []
    if payload.analyses is not None:
        for analysis in payload.analyses:
            row_was_new = False
            row = None
            if analysis.id is not None:
                row = session.get(SampleAnalysis, analysis.id)
            if row is None:
                row = session.exec(
                    select(SampleAnalysis).where(
                        SampleAnalysis.sample_id == sample.id,
                        SampleAnalysis.analysis_type == analysis.analysis_type,
                    )
                ).first()
            if row is None:
                row = SampleAnalysis(
                    sample_id=sample.id,
                    analysis_type=analysis.analysis_type,
                    product_name=analysis.product_name or sample.product_name,
                )
                session.add(row)
                session.commit()
                session.refresh(row)
                row_was_new = True

            before_values = {
                "product_name": row.product_name,
                "temp_obs_f": row.temp_obs_f,
                "lectura_api": row.lectura_api,
                "api_60f": row.api_60f,
                "hydrometer_id": row.hydrometer_id,
                "thermometer_id": row.thermometer_id,
                "water_value": row.water_value,
            }

            row.product_name = analysis.product_name or sample.product_name
            row.temp_obs_f = analysis.temp_obs_f
            row.lectura_api = analysis.lectura_api
            row.hydrometer_id = analysis.hydrometer_id
            row.thermometer_id = analysis.thermometer_id
            row.water_value = analysis.water_value
            if str(row.analysis_type) == SampleAnalysisType.api_astm_1298:
                if row.temp_obs_f is not None and row.lectura_api is not None:
                    row.api_60f = api_60f_crude(row.temp_obs_f, row.lectura_api)
                else:
                    row.api_60f = None
            else:
                row.api_60f = None
            session.add(row)
            analysis_rows.append(row)

            after_values = {
                "product_name": row.product_name,
                "temp_obs_f": row.temp_obs_f,
                "lectura_api": row.lectura_api,
                "api_60f": row.api_60f,
                "hydrometer_id": row.hydrometer_id,
                "thermometer_id": row.thermometer_id,
                "water_value": row.water_value,
            }
            has_changes = row_was_new or any(
                before_values[key] != after_values[key] for key in before_values
            )
            if has_changes and current_user.id is not None:
                history = SampleAnalysisHistory(
                    sample_analysis_id=row.id,
                    sample_id=sample.id,
                    analysis_type=str(row.analysis_type),
                    changed_by_user_id=current_user.id,
                    product_name_before=before_values["product_name"],
                    product_name_after=after_values["product_name"],
                    temp_obs_f_before=before_values["temp_obs_f"],
                    temp_obs_f_after=after_values["temp_obs_f"],
                    lectura_api_before=before_values["lectura_api"],
                    lectura_api_after=after_values["lectura_api"],
                    api_60f_before=before_values["api_60f"],
                    api_60f_after=after_values["api_60f"],
                    hydrometer_id_before=before_values["hydrometer_id"],
                    hydrometer_id_after=after_values["hydrometer_id"],
                    thermometer_id_before=before_values["thermometer_id"],
                    thermometer_id_after=after_values["thermometer_id"],
                    water_value_before=before_values["water_value"],
                    water_value_after=after_values["water_value"],
                )
                session.add(history)
        session.commit()

    analyses = (
        analysis_rows
        if analysis_rows
        else session.exec(
            select(SampleAnalysis).where(SampleAnalysis.sample_id == sample.id)
        ).all()
    )
    return SampleRead(
        id=sample.id,
        terminal_id=sample.terminal_id,
        code=sample.code,
        sequence=sample.sequence,
        created_by_user_id=sample.created_by_user_id,
        created_at=_as_utc(sample.created_at),
        identifier=sample.identifier,
        product_name=sample.product_name,
        analyzed_at=_as_utc(sample.analyzed_at) if sample.analyzed_at else None,
        lab_humidity=sample.lab_humidity,
        lab_temperature=sample.lab_temperature,
        analyses=[
            SampleAnalysisRead.model_validate(r, from_attributes=True)
            for r in analyses
        ],
    )


@router.delete(
    "/{sample_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_sample(
    sample_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(
        require_role(UserType.user, UserType.admin, UserType.superadmin)
    ),
) -> None:
    sample = session.get(Sample, sample_id)
    if not sample:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found",
        )
    _check_terminal_access(session, current_user, sample.terminal_id)

    max_sequence = session.exec(
        select(func.max(Sample.sequence)).where(Sample.terminal_id == sample.terminal_id)
    ).one()
    if max_sequence is None or sample.sequence != max_sequence:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only the latest sample can be deleted",
        )

    terminal = session.get(CompanyTerminal, sample.terminal_id)

    analyses = session.exec(
        select(SampleAnalysis).where(SampleAnalysis.sample_id == sample.id)
    ).all()
    for analysis in analyses:
        if any(
            value is not None
            for value in [
                analysis.api_60f,
                analysis.water_value,
            ]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sample already has data",
            )

    analysis_ids = [analysis.id for analysis in analyses if analysis.id is not None]
    if analysis_ids:
        session.exec(
            delete(SampleAnalysisHistory).where(
                SampleAnalysisHistory.sample_analysis_id.in_(analysis_ids)
            )
        )
    session.exec(
        delete(SampleAnalysisHistory).where(SampleAnalysisHistory.sample_id == sample.id)
    )

    for analysis in analyses:
        session.delete(analysis)

    session.flush()
    session.delete(sample)
    if terminal and terminal.next_sample_sequence == sample.sequence + 1:
        terminal.next_sample_sequence = sample.sequence
        session.add(terminal)

    session.commit()
