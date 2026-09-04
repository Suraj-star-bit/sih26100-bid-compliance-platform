from sqlalchemy import String, Text, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ComplianceResult(Base):
    __tablename__ = "compliance_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    bidder_id: Mapped[int] = mapped_column(
        ForeignKey("bidders.id"),
        nullable=False
    )

    requirement_id: Mapped[int] = mapped_column(
        ForeignKey("requirements.id"),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50)
    )

    score: Mapped[float] = mapped_column(
        Float,
        default=0
    )

    reason: Mapped[str] = mapped_column(
        Text
    )

    evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("extracted_evidence.id"),
        nullable=True
    )