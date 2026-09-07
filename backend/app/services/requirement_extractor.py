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
    "payment of gst",
    "gst shall be paid",
    "gst shall be applicable",
    "gst rate",
    "gst cess",
    "gst compliant bill",
    "gst compliant invoice",
    "tax payable",
    "tax structure",
    "invoice indicating",
    "claim for payment",
    "payment to the contractor",
    "payable gst",
    "payment terms",
    "payment shall",
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

    if len(words) < 8:
        return True

    weak_phrases = [
        "the tender document",
        "tender document",
        "basic tender details",
        "government of india",
        "ministry of",
        "department of",
    ]

    text_lower = text.lower().strip()

    if any(
        phrase in text_lower
        for phrase in weak_phrases
    ):
        return True

    return False