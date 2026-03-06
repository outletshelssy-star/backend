from sqlmodel import Session

from app.core.bootstrap.company import ensure_default_company
from app.core.bootstrap.equipment import ensure_default_equipment
from app.core.bootstrap.equipment_type import (
    ensure_default_equipment_type_inspection_items,
    ensure_default_equipment_type_verifications,
    ensure_default_equipment_types,
)
from app.core.bootstrap.external_analysis import ensure_default_external_analysis_types
from app.core.bootstrap.superadmin import ensure_superadmin
from app.core.config import get_settings
from app.db.engine import engine


def ensure_superadmin_account(*, app_env: str | None = None) -> None:
    settings = get_settings()
    resolved_app_env = app_env or settings.app_env

    if resolved_app_env == "test":
        return

    with Session(engine) as session:
        ensure_superadmin(session)


def should_seed_development_data(
    *, app_env: str, include_development_data: bool | None = None
) -> bool:
    if app_env != "development":
        return False
    if include_development_data is None:
        return True
    return include_development_data


def ensure_bootstrap_data(
    session: Session,
    *,
    app_env: str,
    include_development_data: bool | None = None,
) -> None:
    ensure_superadmin(session)
    ensure_default_company(session)

    if should_seed_development_data(
        app_env=app_env,
        include_development_data=include_development_data,
    ):
        ensure_default_equipment_types(session)
        ensure_default_equipment_type_verifications(session)
        ensure_default_equipment_type_inspection_items(session)
        ensure_default_equipment(session)
        ensure_default_external_analysis_types(session)


def bootstrap_database(
    *,
    app_env: str | None = None,
    include_development_data: bool | None = None,
) -> None:
    settings = get_settings()
    resolved_app_env = app_env or settings.app_env

    if resolved_app_env == "test":
        return

    with Session(engine) as session:
        ensure_bootstrap_data(
            session,
            app_env=resolved_app_env,
            include_development_data=include_development_data,
        )
