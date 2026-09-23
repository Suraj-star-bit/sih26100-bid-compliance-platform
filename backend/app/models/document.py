from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    bidder_id: Mapped[int] = mapped_column(
        ForeignKey("bidders.id"),
        nullable=False
    )

    document_type: Mapped[str] = mapped_column(
        String(100)
    )

    filename: Mapped[str] = mapped_column(
        String(255)
    )

    file_path: Mapped[str] = mapped_column(
        String(500)
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    evidence = relationship(
        "ExtractedEvidence",
        back_populates="document"
    )