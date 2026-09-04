from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Bidder(Base):
    __tablename__ = "bidders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    company_name: Mapped[str] = mapped_column(
        String(255)
    )

    gst_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    pan_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    udyam_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )