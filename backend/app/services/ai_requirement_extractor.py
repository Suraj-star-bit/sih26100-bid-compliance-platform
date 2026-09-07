import json
import ollama
from app.schemas.requirement import ExtractedRequirement
from app.services.clause_extractor import extract_clauses
from app.services.requirement_extractor import is_requirement_candidate

MODEL = "llama3.2:latest"

import re

def evidence_is_grounded(evidence_text, page_text):
    """
    Check whether the AI evidence is actually present in the source text.
    """
    if not evidence_text or not page_text:
        return False

    def normalize(text):
        text = text.lower()
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return " ".join(text.split())

    evidence = normalize(evidence_text)
    source = normalize(page_text)

    if not evidence or not source:
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
            for evidence_word, source_word in zip(evidence_words, window)
            if evidence_word == source_word
        )

        similarity = matches / window_size

        if similarity >= 0.70:
            return True

    return False


def extract_requirements_with_ai(pages):

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

        if not candidate_clauses:
            continue

        page_text = "\n".join(
            clause["text"]
            for clause in candidate_clauses
        )

        prompt = f"""
You are an expert government tender compliance analyst.

Read ONLY the tender text provided below.

Extract ONLY requirements that a BIDDER must satisfy, prove,
declare, possess, or submit for eligibility/compliance.

KEEP:
- bidder registrations and certificates
- bidder eligibility conditions
- documents the bidder must submit
- documents the bidder must provide
- documents the bidder must possess
- declarations required from the bidder
- OEM authorization
- financial requirements such as turnover
- experience requirements
- technical requirements

IGNORE:
- GST/tax calculations
- tax rates
- pricing calculations
- payment instructions
- invoice/payment processing
- instructions meant only for the procuring entity
- headings without an actual requirement
- template placeholders
- examples
- instructions to fill blank fields

For every requirement:
1. Write a short clear description.
2. Identify whether it is mandatory.
3. Extract a required value if one exists.
4. Copy the EXACT supporting text into evidence_text.

IMPORTANT:
The evidence_text MUST be copied directly from the provided tender text.

Do NOT rewrite evidence_text.
Do NOT summarize evidence_text.
Do NOT invent evidence_text.

If there is no clearly supported bidder requirement, return [].

Return ONLY valid JSON in this format:

[
    {{
        "requirement_type": "string",
        "description": "string",
        "required_value": null,
        "mandatory": true,
        "source_page": {page["page_number"]},
        "evidence_text": "exact text from tender"
    }}
]

CRITICAL GROUNDING RULE:

Every requirement MUST be supported by the exact tender text provided below.

Never use knowledge from other tenders, examples, templates, or training data.

Never invent:
- laws
- certificate names
- registration authorities
- numbers
- dates
- thresholds
- company names
- countries
- conditions

A valid compliance requirement must describe something that can be VERIFIED from bidder evidence.

VALID examples:
- bidder must possess GST registration
- bidder must submit registration certificate
- bidder must have minimum annual turnover
- bidder must have required experience
- bidder must submit OEM authorization
- bidder must satisfy a technical specification
- bidder must provide required certificate

INVALID examples:
- bidder must read the tender document
- bidder must follow instructions
- bidder must submit the bid
- bidder must quote prices
- bidder must fill a form
- bidder must sign documents
- bidder must submit the bid before the deadline

Only extract requirements that can later be evaluated as:
COMPLIANT / NON-COMPLIANT / PARTIALLY COMPLIANT / INSUFFICIENT EVIDENCE.

Tender page {page["page_number"]}:

{page_text}
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
            extracted = extracted.get("requirements", [extracted])

        if not isinstance(extracted, list):
            continue

        for requirement in extracted:

            requirement["source_page"] = page["page_number"]

            evidence_text = requirement.get("evidence_text")

            if not evidence_is_grounded(
                evidence_text,
                page_text
            ):
                print(
                    f"Rejected hallucinated requirement on page "
                    f"{page['page_number']}: "
                    f"{requirement.get('requirement_type')}"
                )
                continue

            try:
                results.append(
                    ExtractedRequirement(**requirement)
                )
            except Exception:
                continue

    return results