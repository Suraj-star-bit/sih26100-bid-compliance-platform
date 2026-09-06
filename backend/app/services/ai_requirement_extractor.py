import json
import ollama
from app.schemas.requirement import ExtractedRequirement

MODEL = "llama3.2:latest"

def evidence_is_grounded(evidence_text, page_text):
    """
    Check whether the AI evidence has enough meaningful words
    in the original tender page.
    """
    if not evidence_text or not page_text:
        return False

    evidence_words = set(evidence_text.lower().split())
    source_words = set(page_text.lower().split())

    meaningful_words = {
        word.strip(".,:;()[]'\"")
        for word in evidence_words
        if len(word.strip(".,:;()[]'\"")) >= 4
    }

    if not meaningful_words:
        return False

    matched_words = meaningful_words.intersection(source_words)

    overlap = len(matched_words) / len(meaningful_words)

    return overlap >= 0.30


def extract_requirements_with_ai(pages):

    results = []

    for page in pages:

        prompt = f"""
    You are an expert government tender compliance analyst.

    Read this tender page and extract ONLY requirements that a BIDDER
    must satisfy, prove, declare, or submit for eligibility/compliance.

    KEEP:
    - anything the bidder must submit
    - anything the bidder must provide
    - anything the bidder must possess
    - anything the bidder must declare
    - bidder registrations and certificates
    - bidder eligibility conditions
    - OEM authorization
    - financial requirements such as turnover

    IGNORE ONLY:
    - GST/tax calculations
    - tax rates
    - pricing calculations
    - payment instructions
    - invoice/payment processing
    - instructions meant only for the procuring entity

    For every requirement:
    1. Write a short clear description.
    2. Identify whether it is mandatory.
    3. Extract a required value if one exists.
    4. Copy the EXACT sentence(s) from the page that support the requirement
    into evidence_text.

    Return ONLY this JSON format:

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
    IMPORTANT:
    Extract ONLY requirements that affect whether the BIDDER is compliant or eligible.

    For GST:
    KEEP: GST registration, GSTIN submission, GST certificate, GST exemption declaration.
    IGNORE: GST rates, tax calculations, HSN codes, GST amount, invoices, payment of GST,
    tax structure, tax deductions, and pricing instructions.

    For every requirement, evidence_text MUST contain the exact supporting text from the tender.
    Do not invent or rewrite the evidence_text.

    STRICT GROUNDING RULES:

    - Use ONLY information explicitly present on this tender page.
    - Never invent or guess any requirement.
    - Never create placeholder values such as [Country], [XYZ], [Act/Regulation], or [Timeframe].
    - If a requirement is not clearly supported by the page text, do not extract it.
    - evidence_text MUST be copied directly from the tender page.
    - Do not create evidence_text from a heading alone.
    - Every extracted requirement MUST have supporting evidence in the page text.

    CRITICAL:
    The tender page text below is the ONLY source of truth.

    Before extracting a requirement, verify that the exact meaning and all important details
    appear in the provided page text.

    If the page does not explicitly contain the requirement, return [].

    NEVER use knowledge from other countries, other tenders, examples, templates, or training data.

    NEVER invent:
    - company names
    - countries
    - registration authorities
    - laws
    - certificate names
    - numbers
    - dates
    - thresholds
    - conditions

    The source_page MUST always be the page number provided below.

    Tender page {page["page_number"]}:

    {page["text"]}
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

        for requirement in extracted:
            requirement["source_page"] = page["page_number"]

            if not evidence_is_grounded(
                requirement.get("evidence_text"),
                page["text"]
            ):
                print(
                    f"Rejected hallucinated requirement on page "
                    f"{page['page_number']}: "
                    f"{requirement.get('requirement_type')}"
                )
                continue

            try:
                results.append(ExtractedRequirement(**requirement))
            except Exception:
                continue

    return results