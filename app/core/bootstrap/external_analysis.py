from sqlmodel import Session, select

from app.core.bootstrap.data.external_analyses import DEFAULT_EXTERNAL_ANALYSIS_TYPES
from app.models.enums import UserType
from app.models.external_analysis_type import ExternalAnalysisType
from app.models.user import User


def ensure_default_external_analysis_types(session: Session) -> None:
    superadmin = session.exec(
        select(User).where(User.user_type == UserType.superadmin)
    ).first()
    if not superadmin or superadmin.id is None:
        raise RuntimeError("Superadmin must exist before external analyses")

    for data in DEFAULT_EXTERNAL_ANALYSIS_TYPES:
        existing = session.exec(
            select(ExternalAnalysisType).where(
                ExternalAnalysisType.name == data["name"]
            )
        ).first()
        if existing:
            continue
        session.add(
            ExternalAnalysisType(
                name=data["name"],
                default_frequency_days=data.get("default_frequency_days", 0),
                is_active=data.get("is_active", True),
                created_by_user_id=superadmin.id,
            )
        )
    session.commit()
