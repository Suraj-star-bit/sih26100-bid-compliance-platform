from sqlalchemy.orm import Session

from app.models.compliance import ComplianceResult
from app.models.evidence import ExtractedEvidence
from app.models.requirement import Requirement

from app.services.compliance_engine import evaluate_requirement


def evaluate_bidder_compliance(
    db: Session,
    bidder_id: int,
    tender_id: int,
) -> list[ComplianceResult]:

    requirements = (
        db.query(Requirement)
        .filter(Requirement.tender_id == tender_id)
        .all()
    )

    results = []

    for requirement in requirements:

        evidence_list = (
            db.query(ExtractedEvidence)
            .join(
                ExtractedEvidence.document
            )
            .filter(
                ExtractedEvidence.document.has(
                    bidder_id=bidder_id
                )
            )
            .all()
        )

        result = evaluate_requirement(
            requirement,
            evidence_list
        )

        compliance_result = ComplianceResult(
            bidder_id=bidder_id,
            requirement_id=requirement.id,
            status=result["status"],
            score=result["score"],
            reason=result["reason"],
            evidence_id=result["evidence_id"],
        )

        db.add(compliance_result)
        results.append(compliance_result)

    db.commit()

    return results