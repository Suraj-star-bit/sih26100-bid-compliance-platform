from typing import Iterable


COMPLIANT = "COMPLIANT"
NON_COMPLIANT = "NON_COMPLIANT"
PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    return " ".join(value.lower().strip().split())


def check_text_requirement(
    requirement,
    evidence_list: Iterable
) -> dict:
    evidence_list = list(evidence_list)

    if not evidence_list:
        return {
            "status": INSUFFICIENT_EVIDENCE,
            "score": 0,
            "reason": "No supporting evidence was found.",
            "evidence_id": None,
        }

    valid_evidence = [
        evidence
        for evidence in evidence_list
        if normalize_text(evidence.extracted_value)
    ]

    if not valid_evidence:
        return {
            "status": INSUFFICIENT_EVIDENCE,
            "score": 0,
            "reason": "Evidence records were found, but no usable value was extracted.",
            "evidence_id": None,
        }

    evidence = valid_evidence[0]

    return {
        "status": COMPLIANT,
        "score": 100,
        "reason": (
            f"Supporting evidence was found: "
            f"{evidence.extracted_value}"
        ),
        "evidence_id": evidence.id,
    }


def evaluate_requirement(
    requirement,
    evidence_list: Iterable
) -> dict:

    requirement_type = normalize_text(
        requirement.requirement_type
    )

    if requirement_type in {
    "numeric",
    "turnover",
    "experience_count",
    "technical_specification",
}:
        return check_numeric_requirement(
            requirement,
            evidence_list
        )

    if requirement_type in {
        "registration",
        "certificate",
        "declaration",
        "eligibility",
        "document_submission",
    }:
        return check_text_requirement(
            requirement,
            evidence_list
        )

    return check_text_requirement(
        requirement,
        evidence_list
    )

def check_numeric_requirement(
    requirement,
    evidence_list: Iterable
) -> dict:
    evidence_list = list(evidence_list)

    if not evidence_list:
        return {
            "status": INSUFFICIENT_EVIDENCE,
            "score": 0,
            "reason": "No supporting evidence was found.",
            "evidence_id": None,
        }

    required_value = requirement.required_value

    if not required_value:
        return check_text_requirement(
            requirement,
            evidence_list
        )

    try:
        required_number = float(required_value)
    except ValueError:
        return check_text_requirement(
            requirement,
            evidence_list
        )

    for evidence in evidence_list:
        try:
            actual_number = float(evidence.extracted_value)
        except (ValueError, TypeError):
            continue

        if actual_number >= required_number:
            return {
                "status": COMPLIANT,
                "score": 100,
                "reason": (
                    f"Required value: {required_number}. "
                    f"Bidder value: {actual_number}."
                ),
                "evidence_id": evidence.id,
            }

    return {
        "status": NON_COMPLIANT,
        "score": 0,
        "reason": (
            f"The bidder's evidence did not meet "
            f"the required value of {required_number}."
        ),
        "evidence_id": evidence_list[0].id,
    }