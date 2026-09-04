from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    tender_id: Mapped[int] = mapped_column(
        ForeignKey("tenders.id"),
        nullable=False
    )

    requirement_type: Mapped[str] = mapped_column(
        String(100)
    )

    description: Mapped[str] = mapped_column(Text)

    required_value: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    source_page: Mapped[int | None] = mapped_column(
        nullable=True
    )

    mandatory: Mapped[bool] = mapped_column(
        default=True
    )