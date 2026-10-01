import re
from app.services.tender_blocks import build_text_blocks

REQUIREMENT_WORDS = [
    "must",
    "shall",
    "should",
    "required",
    "mandatory",
    "submit",
    "furnish",
    "provide",
    "possess",
    "ensure",
    "eligible",
    "eligibility",
]


TEMPLATE_PHRASES = [
    "[fill]",
    "[if applicable]",
    "[insert",
    "[mention",
    "[description of",
    "[to be specified]",
    "[xyz]",
    "[country]",
    "[timeframe]",
    "tend no./ xxxx",
]


EXCLUDED_PHRASES = [
    # Pricing / financial instructions
    "price schedule",
    "price quoted",
    "prices quoted",
    "quoted price",
    "bid price",
    "bid prices",
    "price variation",
    "price components",
    "unit prices",
    "total bid prices",
    "financial bid",
    "financial bids",
    "payment terms",
    "payment shall",
    "advance payment",
    "payment to the contractor",
    "payable to the contractor",

    # Tax / GST pricing — NOT GST registration
    "gst rate",
    "gst rates",
    "gst amount",
    "gst cess",
    "tax structure",
    "tax payable",
    "tax rate",
    "tax rates",
    "hsn code",
    "input credit",
    "customs duty",

    # Tender process / administrative instructions
    "download the tender",
    "downloading the tender",
    "clarification of the tender",
    "seek clarification",
    "pre-bid conference",
    "pre bid conference",
    "corrigenda",
    "addenda",
    "deadline for availability",
    "deadline for clarification",

    # General bid preparation
    "cost of bidding",
    "costs associated with",
    "costs incurred in connection",
    "language of the bid",
    "alternative bids",
    "alternative offers",
    "multiple bids",

    "quote quantities",
    "quote quantities / prices",
    "quantities / prices",
    "quoted in numerals",
    "quoted in words",
    "visit the site",
    "visit the site / local conditions",
    "familiarise himself with the site",
    "familiarize himself with the site",
]


NON_COMPLIANCE_REQUIREMENTS = [
    "read the complete tender document",
    "read the tender document",
    "bidders must read",
    "bidder must read",
    "submit the bid before",
    "submit your bid before",
    "follow the instructions",
    "fill in the form",
    "fill the form",
    "sign the form",
    "download the tender document",
    "download tender document",
    "seek clarification",
    "attend the pre-bid conference",
]


BIDDER_CONTEXT = [
    "bidder",
    "bidders",
    "tenderer",
    "vendor",
    "contractor",
    "oem",
    "manufacturer",
    "supplier",
    "pan",
    "authorization certificate",
    "authorization",
    "certificate",
]
NON_COMPLIANCE_REQUIREMENTS = [
    "read the complete tender document",
    "read the tender document",
    "bidders must read",
    "bidder must read",
    "quote the prices",
    "submit the bid before",
    "submit your bid before",
    "follow the instructions",
    "fill in the form",
    "fill the form",
    "sign the form",
    "download the tender document",
]

def contains_requirement_word(text: str) -> bool:
    text = text.lower()

    return any(
        re.search(rf"\b{re.escape(word)}\b", text)
        for word in REQUIREMENT_WORDS
    )


def contains_template_placeholder(text: str) -> bool:
    text = text.lower()

    return any(
        phrase in text
        for phrase in TEMPLATE_PHRASES
    )


def is_excluded_clause(text: str) -> bool:
    text = text.lower()

    # GST registration is a genuine bidder compliance requirement.
    # Do not reject the whole clause just because the surrounding
    # GST section also contains tax/pricing information.
    if "gst registration" in text or "gstin" in text:
        return False

    return any(
        phrase in text
        for phrase in EXCLUDED_PHRASES
    )


def refers_to_bidder(text: str) -> bool:
    text = text.lower()

    return any(
        re.search(rf"\b{re.escape(word)}\b", text)
        for word in BIDDER_CONTEXT
    )


def is_requirement_candidate(text: str) -> bool:
    if not text:
        return False

    if is_weak_requirement_block(text):
        return False

    if contains_template_placeholder(text):
        return False

    if is_excluded_clause(text):
        return False

    if is_non_compliance_requirement(text):
        return False

    if not contains_requirement_word(text):
        return False

    if not refers_to_bidder(text):
        return False

    return True

ALLOWED_AI_TYPES = {
    "eligibility",
    "registration",
    "certificate",
    "declaration",
    "financial",
    "turnover",
    "experience",
    "technical",
    "document_submission",
}


INVALID_REQUIREMENT_PHRASES = [
    "read the complete tender document",
    "read the tender document",
    "basic tender details",
    "provide basic details",
    "must provide basic tender details",
    "must read the complete",
    "criteria that a bidder must meet",
    "bidders must meet the eligibility criteria",
]


def is_valid_ai_requirement(requirement: dict) -> bool:
    requirement_type = (
        requirement.get("requirement_type") or ""
    ).strip().lower()

    description = (
        requirement.get("description") or ""
    ).strip().lower()

    evidence_text = (
        requirement.get("evidence_text") or ""
    ).strip()

    if requirement_type not in ALLOWED_AI_TYPES:
        return False

    if not description:
        return False

    if not evidence_text:
        evidence_text = description

    if any(
        phrase in description
        for phrase in INVALID_REQUIREMENT_PHRASES
    ):
        return False

    return True

GST_NON_COMPLIANCE_PHRASES = [
    "gst cess",
    "payable gst",
    "gst under the rcm",
    "rcm",
    "gst payable",
    "gst rate",
    "gst rates",
    "tax structure",
    "tax payable",
    "tax rate",
]


def is_useful_ai_requirement(requirement: dict) -> bool:
    description = (
        requirement.get("description") or ""
    ).strip().lower()

    evidence = (
        requirement.get("evidence_text") or ""
    ).strip().lower()

    combined = f"{description} {evidence}"

    if any(phrase in description for phrase in GST_NON_COMPLIANCE_PHRASES):
        return False

    if any(phrase in description for phrase in [
        "procuring entity's state-wise gstin",
        "procuring entity gstin",
    ]):
        return False

    if "gst cess" in combined and "registration" not in combined:
        return False

    if "gst payable" in combined and "registration" not in combined:
        return False

    return True

def normalize_requirement_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def is_duplicate_requirement(
    requirement: dict,
    existing_requirements: list
) -> bool:

    description = normalize_requirement_text(
        requirement.get("description") or ""
    )

    if not description:
        return False

    for existing in existing_requirements:

        existing_description = normalize_requirement_text(
            existing.description
        )

        if description == existing_description:
            return True

    return False


def split_combined_requirement(requirement: dict) -> list[dict]:

    description = requirement.get("description") or ""

    protected_description = re.sub(
        r"\bRs\.",
        "Rs",
        description,
        flags=re.IGNORECASE
    )

    sentences = re.split(
        r"(?<=[.!?])\s+",
        protected_description.strip()
    )

    results = []

    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue

        sentence = re.sub(
            r"\bRs(?=\s)",
            "Rs.",
            sentence,
            flags=re.IGNORECASE
        )

        lower_sentence = sentence.lower()

        new_requirement = requirement.copy()
        new_requirement["description"] = sentence

        if "gst registration" in lower_sentence:
            new_requirement["requirement_type"] = "registration"
            new_requirement["required_value"] = None

        elif "gstin" in lower_sentence:
            new_requirement["requirement_type"] = "registration"
            new_requirement["required_value"] = None

        elif "oem authorization" in lower_sentence:
            new_requirement["requirement_type"] = "certificate"
            new_requirement["required_value"] = None

        elif (
            "annual turnover" in lower_sentence
            or "average annual turnover" in lower_sentence
            or "minimum turnover" in lower_sentence
        ):
            new_requirement["requirement_type"] = "turnover"

        elif (
            "turnover" in lower_sentence
            and any(
                symbol in lower_sentence
                for symbol in [">=", ">", "at least", "minimum", "not less than", "rs."]
            )
        ):
            new_requirement["requirement_type"] = "turnover"

        else:
            continue

        results.append(new_requirement)

    return results if results else [requirement]

def get_mandatory(text: str) -> bool:

    text = text.lower()

    mandatory_words = [
        "must",
        "shall",
        "mandatory",
        "required",
    ]

    optional_phrases = [
        "if applicable",
        "where applicable",
        "may submit",
        "optional",
    ]

    if any(phrase in text for phrase in optional_phrases):
        return False

    return any(
        re.search(rf"\b{re.escape(word)}\b", text)
        for word in mandatory_words
    )


def detect_requirement_type(text: str) -> str:

    text = text.lower()

    if re.search(r"\bgst(?:in)?\b|gst registration|gst certificate", text):
        return "gst"

    if re.search(r"\bpan\b|pan card", text):
        return "pan"

    if re.search(r"\budyam\b|\bmsme\b", text):
        return "udyam_msme"

    if re.search(r"\boem\b|manufacturer authorization", text):
        return "oem_authorization"

    if re.search(r"turnover|annual turnover", text):
        return "turnover"

    if re.search(r"similar work|similar project|experience", text):
        return "experience"

    if re.search(r"technical specification|technical requirement", text):
        return "technical"

    return "other"


def extract_required_value(text: str) -> str | None:

    turnover_match = re.search(
        r"(?:turnover|annual turnover)"
        r".{0,150}?"
        r"(?:₹|rs\.?|inr)?\s*"
        r"([\d,.]+)\s*"
        r"(crore|crores|lakh|lakhs)?",
        text,
        re.IGNORECASE,
    )

    if turnover_match:

        value = turnover_match.group(1)

        unit = turnover_match.group(2)

        if unit:
            value += f" {unit}"

        return value

    return None


def build_candidate(text: str, page_number: int):

    if not is_requirement_candidate(text):
        return None

    return {
        "requirement_type": detect_requirement_type(text),
        "description": text.strip(),
        "required_value": extract_required_value(text),
        "mandatory": get_mandatory(text),
        "source_page": page_number,
    }
def extract_requirements(pages):

    requirements = []

    for page in pages:

        page_number = page["page_number"]

        # Convert raw PDF lines into meaningful text blocks
        blocks = build_text_blocks(page["text"])

        for block in blocks:

            candidate = build_candidate(
                block,
                page_number
            )

            if candidate:
                requirements.append(candidate)

    return requirements

def is_non_compliance_requirement(text: str) -> bool:
    text = text.lower()
    return any(
        phrase in text
        for phrase in NON_COMPLIANCE_REQUIREMENTS
    )

def is_weak_requirement_block(text: str) -> bool:
    words = text.split()

    if len(words) < 4:
        return True

    return False