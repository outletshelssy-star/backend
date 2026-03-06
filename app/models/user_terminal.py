from sqlmodel import Field, SQLModel, UniqueConstraint


class UserTerminal(SQLModel, table=True):
    __tablename__ = "user_terminal"
    __table_args__ = (
        UniqueConstraint("user_id", "terminal_id", name="uq_user_terminal"),
    )
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    terminal_id: int = Field(foreign_key="company_terminal.id")
