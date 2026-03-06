from sqlmodel import Field, SQLModel, UniqueConstraint

from app.models.enums import ProductType
from app.models.mixins.audit import AuditMixin


class TerminalProduct(AuditMixin, SQLModel, table=True):
    __tablename__ = "terminal_product_type"
    __table_args__ = (UniqueConstraint("terminal_id", "name", name="uq_terminal_product_name"),)

    id: int | None = Field(default=None, primary_key=True)
    terminal_id: int = Field(foreign_key="company_terminal.id", index=True)
    name: str = Field(min_length=1, max_length=120)
    product_type: ProductType


# Backward-compatible alias.
TerminalProductType = TerminalProduct
