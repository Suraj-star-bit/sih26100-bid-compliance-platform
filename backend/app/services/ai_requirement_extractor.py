import json
import re

import ollama

from app.schemas.requirement import ExtractedRequirement
from app.services.clause_extractor import extract_clauses
from app.services.requirement_extractor import is_requirement_candidate


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
    clause_text: str
) -> str | None:

    explicit_value = extract_explicit_value(clause_text)

    if explicit_value:
        return explicit_value

    if not ai_value:
        return None

    normalized_ai_value = normalize(ai_value)
    normalized_clause = normalize(clause_text)

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


def extract_requirements_with_ai(pages):

    results = []

    for page in pages:

        clauses = extract_clauses(
            page["page_number"],
            page["text"]
        )

        candidate_clauses = clauses

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
other

For every requirement:

1. Write a short, specific description.

2. Identify whether it is mandatory.

3. Extract required_value only when the value is explicitly
   written in THIS clause.

4. evidence_text must contain the exact supporting statement
   from THIS clause.

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
            "evidence_text": "exact text from tender"
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

                evidence_text = improve_evidence(
                    requirement.get("evidence_text"),
                    clause_text
                )
                description = requirement.get("description")
                if not description or description.strip().lower() == "string":
                    description = evidence_text

                ai_evidence = requirement.get("evidence_text")

                if not ai_evidence:
                    continue

                normalized_clause = normalize(clause_text)
                normalized_evidence = normalize(ai_evidence)

                if normalized_evidence not in normalized_clause:
                    continue

                # Use the original clause as the authoritative evidence.
                evidence_text = clause_text.strip()

                required_value = clean_required_value(
                    requirement.get("required_value"),
                    clause_text
                )

                description = requirement.get("description")

                if not description or description.strip().lower() == "string":
                    description = evidence_text

                requirement["description"] = description.strip()
                requirement["evidence_text"] = evidence_text
                requirement["required_value"] = required_value

                if not evidence_text:
                    print(
                        f"Rejected unsupported evidence on "
                        f"page {page['page_number']}, "
                        f"clause {clause['clause']}"
                    )
                    continue

                required_value = clean_required_value(
                    requirement.get("required_value"),
                    clause_text
                )

                requirement["required_value"] = required_value
                requirement["evidence_text"] = evidence_text

                requirement["source_page"] = (
                    page["page_number"]
                )

                requirement["source_section"] = (
                    f"Clause {clause['clause']}"
                    if clause["clause"]
                    else None
                )

                try:
                    results.append(
                        ExtractedRequirement(**requirement)
                    )

                except Exception as e:
                    print(
                        f"Invalid requirement skipped: {e}"
                    )

    return results