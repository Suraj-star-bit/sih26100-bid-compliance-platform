import re


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
]


def contains_requirement_word(line: str) -> bool:
    return any(
        re.search(rf"\b{re.escape(word)}\b", line.lower())
        for word in REQUIREMENT_WORDS
    )


def is_bidder_requirement(line: str) -> bool:
    text = line.lower()

    # Reject tax/payment/invoice clauses
    excluded_phrases = [
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
    ]

    if any(phrase in text for phrase in excluded_phrases):
        return False

    # A compliance requirement should normally refer to the bidder/vendor
    bidder_context = [
        "bidder",
        "bidders",
        "tenderer",
        "vendor",
        "contractor",
        "oem",
        "documents to be submitted",
    ]

    return any(word in text for word in bidder_context)


def get_mandatory(line: str) -> bool:
    text = line.lower()

    if "if applicable" in text:
        return False

    strong_words = [
        "must",
        "shall",
        "mandatory",
        "required",
    ]

    return any(
        re.search(rf"\b{re.escape(word)}\b", text)
        for word in strong_words
    )


def extract_requirements(pages):

    requirements = []

    patterns = {
        "turnover": r"(?:turnover|annual turnover).*?(?:₹|rs\.?|inr)?\s*([\d,.]+)\s*(crore|lakh)?",
        "gst": r"\bGST(?:IN)?\b",
        "pan": r"\bPAN\b",
        "udyam": r"\bUdyam\b|\bMSME\b",
        "oem": r"\bOEM\b|manufacturer authorization",
    }

    for page in pages:

        page_number = page["page_number"]

        for line in page["text"].splitlines():

            line = line.strip()

            if not line:
                continue

            if not contains_requirement_word(line):
                continue

            if not is_bidder_requirement(line):
                continue

            for requirement_type, pattern in patterns.items():

                match = re.search(
                    pattern,
                    line,
                    re.IGNORECASE
                )

                if not match:
                    continue

                required_value = None

                if requirement_type == "turnover":
                    value = match.group(1)

                    if value and re.search(r"\d", value):
                        required_value = value

                        if match.group(2):
                            required_value += f" {match.group(2)}"

                requirements.append({
                    "requirement_type": requirement_type,
                    "description": line,
                    "required_value": required_value,
                    "mandatory": get_mandatory(line),
                    "source_page": page_number
                })

    return requirements