from datetime import UTC, datetime

from sqlmodel import Session, select

from app.models.enums import EquipmentStatus
from app.models.equipment_status_history import EquipmentStatusHistory


def record_equipment_status_change(
    session: Session,
    equipment_id: int,
    new_status: EquipmentStatus,
    changed_by_user_id: int,
) -> None:
    current_status_history = session.exec(
        select(EquipmentStatusHistory).where(
            EquipmentStatusHistory.equipment_id == equipment_id,
            EquipmentStatusHistory.ended_at.is_(None),  # type: ignore[union-attr]
        )
    ).first()

    if current_status_history and current_status_history.status == new_status:
        return

    now = datetime.now(UTC)
    if current_status_history:
        current_status_history.ended_at = now
        session.add(current_status_history)

    session.add(
        EquipmentStatusHistory(
            equipment_id=equipment_id,
            status=new_status,
            changed_by_user_id=changed_by_user_id,
            started_at=now,
        )
    )
