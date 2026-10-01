import json
import re

import ollama

from app.schemas.requirement import ExtractedRequirement
from app.services.clause_extractor import extract_clauses
from app.services.requirement_extractor import (
    is_requirement_candidate,
    is_valid_ai_requirement,
    is_useful_ai_requirement,
    split_combined_requirement,
    is_duplicate_requirement,
)

from app.models.requirement import Requirement


MODEL = "llama3.2:latest"


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def evidence_is_grounded(evidence_text: str, source_text: str) -> bool:
    if not evidence_text or not source_text:
        return False

    evidence = normalize(evidence_text)
    source = normalize(source_text)

    if not evidence:
        return False

    if evidence in source:
        return True

    evidence_words = evidence.split()
    source_words = source.split()

    if len(evidence_words) < 5:
        return False

    window_size = len(evidence_words)

    for i in range(len(source_words) - window_size + 1):
        window = source_words[i:i + window_size]

        matches = sum(
            1
            for evidence_word, source_word in zip(
                evidence_words,
                window
            )
            if evidence_word == source_word
        )

        similarity = matches / window_size

        if similarity >= 0.70:
            return True

    return False


def find_full_sentence(source_text: str, evidence_text: str) -> str | None:
    """
    If AI returns only part of a sentence, return the complete
    sentence from the original tender text.
    """
    if not evidence_text:
        return None

    normalized_evidence = normalize(evidence_text)

    sentences = re.split(
        r"(?<=[.!?])\s+",
        source_text
    )

    for sentence in sentences:
        if normalized_evidence in normalize(sentence):
            return sentence.strip()

    return None


def extract_explicit_value(text: str) -> str | None:
    """
    Extract values explicitly present in the original tender text.
    """

    form_match = re.search(
        r"\bForm\s+([A-Za-z0-9.\-]+)\s*[–—-]\s*([A-Za-z][^\n]+)",
        text,
        re.IGNORECASE
    )

    if form_match:
        form_number = form_match.group(1).strip()
        form_name = form_match.group(2).strip()

        return f"Form {form_number} – {form_name}"

    turnover_match = re.search(
        r"(?:turnover|annual turnover)"
        r".{0,150}?"
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,.]+)\s*"
        r"(crore|crores|lakh|lakhs)?",
        text,
        re.IGNORECASE
    )

    if turnover_match:
        value = turnover_match.group(1)
        unit = turnover_match.group(2)

        if unit:
            value += f" {unit}"

        return value

    return None


def clean_required_value(
    ai_value: str | None,
    clause_text: str,
    requirement_type: str | None = None
) -> str | None:

    requirement_type = (requirement_type or "").strip().lower()

    non_numeric_types = {
        "registration",
        "certificate",
        "declaration",
        "eligibility",
        "document_submission",
    }

    if requirement_type in non_numeric_types:
        return None

    explicit_value = extract_explicit_value(clause_text)

    if explicit_value:
        return explicit_value

    if not ai_value:
        return None

    normalized_ai_value = normalize(ai_value)
    normalized_clause = normalize(clause_text)

    # Reject obviously invalid AI values
    if normalized_ai_value in {"", ",", ".", ":", "-", "none", "null"}:
        return None

    if normalized_ai_value in normalized_clause:
        return ai_value.strip()

    return None


def improve_evidence(
    ai_evidence: str | None,
    clause_text: str
) -> str | None:

    if not ai_evidence:
        return None

    if not evidence_is_grounded(
        ai_evidence,
        clause_text
    ):
        return None

    normalized_clause = normalize(clause_text)
    normalized_evidence = normalize(ai_evidence)

    start = normalized_clause.find(
        normalized_evidence
    )

    if start == -1:
        return ai_evidence.strip()

    return ai_evidence.strip()

def extract_requirements_with_ai(
    pages,
    tender_id,
    db
):

    results = []

    for page in pages:

        clauses = extract_clauses(
            page["page_number"],
            page["text"]
        )

        candidate_clauses = [
    clause
        for clause in clauses
        if is_requirement_candidate(clause["text"])
    ]

        for clause in candidate_clauses:

            clause_text = clause["text"]

            prompt = f"""
You are an expert government tender compliance analyst.

Read ONLY the tender clause provided below.

Extract ONLY requirements that a BIDDER must satisfy, prove,
declare, possess, or submit.

KEEP:
- bidder eligibility conditions
- bidder registrations
- certificates
- declarations
- document submissions
- financial requirements
- turnover requirements
- experience requirements
- technical requirements
- OEM authorization
- qualification requirements

IGNORE:
- GST/tax calculations
- tax rates
- pricing calculations
- payment instructions
- invoice/payment processing
- procuring entity instructions
- headings without requirements
- template placeholders
- examples
- background information

A requirement must be something that can later be evaluated as:

COMPLIANT
NON-COMPLIANT
PARTIALLY COMPLIANT
INSUFFICIENT EVIDENCE

requirement_type MUST be one of:

eligibility
registration
certificate
declaration
financial
experience
technical
document_submission

For every requirement:

1. Write a short, specific description.

IMPORTANT:
Extract each independently checkable bidder obligation as ONE requirement.

Do NOT create separate requirements for individual words,
documents, or pieces of evidence that belong to the same obligation.

For example, if a clause says:

"Bidder should be registered under GST and furnish GSTIN
and GST Registration Certificate."

return ONE requirement:

- Type: registration
- Description: Bidder must be registered under GST and furnish GSTIN and GST Registration Certificate.

Do NOT create separate requirements for:
- GST registration
- GSTIN
- GST Registration Certificate

because these are parts of the same bidder obligation.

However, if a clause contains genuinely independent obligations,
extract them separately.

For example, if a clause says the bidder must:
- have an annual turnover of Rs. 10 Crore
- possess valid GST registration

return TWO requirements.

Similarly, if a clause independently requires:
- PAN submission
- OEM authorization

return TWO requirements.

A document, certificate, number, or declaration should NOT become
a separate requirement if it is only supporting evidence for
another requirement.

Each requirement should represent something that can be evaluated
independently as:

COMPLIANT
NON_COMPLIANT
PARTIALLY_COMPLIANT
INSUFFICIENT_EVIDENCE

2. Identify whether it is mandatory.

3. Extract required_value only when the value is explicitly
    written in THIS clause.

4. evidence_text must be an EXACT VERBATIM substring copied
    from THIS clause.

    The evidence_text MUST literally appear in the Tender clause text.

    NEVER use placeholder text such as:
    "exact text from tender"
    "exact supporting statement"
    "string"
    or any similar placeholder.

    Copy the actual words from the Tender clause.
    Do NOT paraphrase.
    Do NOT summarize.
    Do NOT invent.
IMPORTANT:

Never invent a value.

Never infer a form number.

Never infer a certificate name.

Never infer a threshold.

Never infer a date.

Never infer a registration number.

If a value is not explicitly present in the clause,
required_value MUST be null.

For document submission requirements, include the complete
submission statement as evidence.

If the clause says:

"Bidder shall submit a declaration about the Eligibility Criteria
compliance in Form 1.2 – Eligibility Declarations."

the evidence should contain that complete statement.

Do NOT stop evidence at "Form".

Do NOT rewrite evidence_text.
Do NOT summarize evidence_text.
Do NOT invent evidence_text.

If the clause does not contain enough information to support
a separate requirement, do not extract it.

Do NOT generate source_page.
The backend assigns the source page.

Return ONLY valid JSON:

{{
    "requirements": [
        {{
            "requirement_type": "eligibility",
            "description": "string",
            "required_value": null,
            "mandatory": true,
            "evidence_text": "Bidder shall submit the required document"
        }}
    ]
}}

Tender page: {page["page_number"]}
Clause: {clause["clause"]}

Tender clause text:

{clause_text}
"""

            response = ollama.chat(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                format="json"
            )

            content = response["message"]["content"]

            print("\n--- OLLAMA RAW RESPONSE ---")
            print(content)
            print("---------------------------\n")

            try:
                extracted = json.loads(content)
            except json.JSONDecodeError:
                continue

            if isinstance(extracted, dict):
                extracted = extracted.get(
                    "requirements",
                    []
                )

            if not isinstance(extracted, list):
                continue

            for requirement in extracted:

                split_requirements = split_combined_requirement(
                    requirement
                )

                for requirement in split_requirements:

                    if not is_valid_ai_requirement(requirement):
                        print(
                            f"Rejected invalid AI requirement on "
                            f"page {page['page_number']}"
                        )
                        continue
                    if not is_useful_ai_requirement(requirement):
                        print(
                            f"Rejected non-compliance AI requirement on page {page['page_number']}"
                        )
                        continue

                    ai_evidence = requirement.get("evidence_text")

                    # Ollama sometimes omits evidence_text.
                    # Use the AI description as the evidence candidate in that case.
                    if not ai_evidence:
                        ai_evidence = requirement.get("description")

                    if not ai_evidence:
                        print(
                            f"Rejected requirement without evidence on "
                            f"page {page['page_number']}"
                        )
                        continue

                    # Verify that the AI evidence is actually supported
                    # by the original tender clause.
                    grounded_evidence = improve_evidence(
                        ai_evidence,
                        clause_text
                    )

                    if not grounded_evidence:
                        print(
                            f"Rejected unsupported evidence on "
                            f"page {page['page_number']}, "
                            f"clause {clause['clause']}"
                        )
                        continue

                    requirement["evidence_text"] = grounded_evidence

                    # Ollama may also omit mandatory.
                    # Tender compliance requirements are mandatory by default.
                    if "mandatory" not in requirement:
                        requirement["mandatory"] = True

                    # Keep the AI evidence only if it is grounded in the original clause.
                    evidence_text = requirement.get("evidence_text")

                    if not evidence_text:
                        print(
                            f"Rejected unsupported evidence on "
                            f"page {page['page_number']}, "
                            f"clause {clause['clause']}"
                        )
                        continue

                    description = requirement.get("description")

                    if (
                        not description
                        or description.strip().lower() == "string"
                    ):
                        description = evidence_text

                    required_value = clean_required_value(
                        requirement.get("required_value"),
                        clause_text,
                        requirement.get("requirement_type")
                    )

                    requirement["description"] = description.strip()
                    requirement["evidence_text"] = evidence_text
                    requirement["required_value"] = required_value

                    requirement["source_page"] = (
                        page["page_number"]
                    )

                    requirement["source_section"] = (
                        f"Clause {clause['clause']}"
                        if clause["clause"]
                        else None
                    )

                    if is_duplicate_requirement(
                        requirement,
                        results
                    ):
                        print(
                            f"Duplicate requirement skipped on "
                            f"page {page['page_number']}"
                        )
                        continue

                    try:
                        db_requirement = Requirement(
                            tender_id=tender_id,
                            requirement_type=requirement[
                                "requirement_type"
                            ],
                            description=requirement[
                                "description"
                            ],
                            required_value=requirement[
                                "required_value"
                            ],
                            source_page=requirement[
                                "source_page"
                            ],
                            mandatory=requirement[
                                "mandatory"
                            ],
                            evidence_text=requirement[
                                "evidence_text"
                            ],
                        )

                        db.add(db_requirement)
                        db.flush()

                        results.append(db_requirement)

                    except Exception as e:
                        print(
                            f"Failed to save requirement: {e}"
                        )

                db.commit()

        return results