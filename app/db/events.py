from sqlalchemy import event
from sqlmodel import SQLModel

from app.models.mixins.audit import AuditMixin


@event.listens_for(SQLModel, "before_update", propagate=True)
def receive_before_update(mapper, connection, target):
    if isinstance(target, AuditMixin):
        AuditMixin.update_timestamp(mapper, connection, target)
