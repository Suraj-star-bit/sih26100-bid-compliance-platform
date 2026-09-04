from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ExtractedEvidence(Base):
    __tablename__ = "extracted_evidence"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id"),
        nullable=False
    )

    field_name: Mapped[str] = mapped_column(
        String(100)
    )

    extracted_value: Mapped[str] = mapped_column(
        Text
    )

    source_page: Mapped[int | None] = mapped_column(
        nullable=True
    )

    confidence: Mapped[float | None] = mapped_column(
        nullable=True
    )