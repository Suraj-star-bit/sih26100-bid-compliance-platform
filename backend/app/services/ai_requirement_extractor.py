import json
import ollama

from app.schemas.requirement import ExtractedRequirement


MODEL = "llama3.2:latest"


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
            extracted = [extracted]

        for requirement in extracted:

            requirement["source_page"] = page["page_number"]

            try:
                results.append(
                    ExtractedRequirement(**requirement)
                )
            except Exception:
                continue

    return results